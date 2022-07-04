# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import utime
import modem
import osTimer

from usr.modules.sensor import Sensor
from usr.modules.battery import Battery
from usr.modules.history import History
from usr.modules.logging import getLogger
from usr.modules.mpower import LowEnergyManage
from usr.modules.temp_humidity_sensor import TempHumiditySensor
from usr.modules.common import Singleton, LOWENERGYMAP
from usr.modules.location import Location, GPSMatch, GPSParse, _loc_method
from usr.settings import PROJECT_NAME, PROJECT_VERSION, DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION, \
    settings, UserConfig, SYSConfig
from usr.tracker_controller import Controller
from usr.tracker_devicecheck import DeviceCheck

log = getLogger(__name__)


ALERTCODE = {
    20000: "fault_alert",
    30002: "low_power_alert",
    30003: "over_speed_alert",
    30004: "sim_abnormal_alert",
    30005: "disassemble_alert",
    40000: "drive_behavior_alert",
    50001: "sos_alert",
}


class Collector(Singleton):
    """Device data and commands collector"""
    def __init__(self):
        self.__controller = None
        self.__devicecheck = None
        self.__battery = None
        self.__sensor = None
        self.__locator = None
        self.__history = None
        self.__temp_humidity_sensor = None
        self.__gps_match = GPSMatch()
        self.__gps_parse = GPSParse()

        self.__net_status = False
        self.__loc_status = False

    def __format_loc_method(self, data):
        """Decimal to Binary for loc method
        The first is gps, second is cell, third is wifi from binary right.
        """
        loc_method = "%04d" % int(bin(data)[2:])
        gps = bool(int(loc_method[-1]))
        cell = bool(int(loc_method[-2]))
        wifi = bool(int(loc_method[-3]))

        loc_method = {
            "gps": gps,
            "cell": cell,
            "wifi": wifi,
        }
        return loc_method

    def __get_local_time(self):
        """Get millisecond timestamp"""
        return str(utime.mktime(utime.localtime()) * 1000)

    def __get_alert_data(self, alert_code, alert_info):
        """Get alert data by alert code"""
        current_settings = settings.get()
        alert_data = {}
        if ALERTCODE.get(alert_code):
            alert_status = current_settings.get("user_cfg", {}).get("sw_" + ALERTCODE.get(alert_code))
            if alert_status:
                alert_data = {ALERTCODE.get(alert_code): alert_info}
            else:
                log.warn("%s switch is %s" % (ALERTCODE.get(alert_code), alert_status))
        else:
            log.error("altercode (%s) is not exists. alert info: %s" % (alert_code, alert_info))

        return alert_data

    def __init_low_energy_method(self, period):
        """Auto set low energy method
        1. Get device support method.
        2. Compare low energy period with user set work_mode_timeline.
        """
        current_settings = settings.get()
        device_model = modem.getDevModel()
        support_methods = LOWENERGYMAP.get(device_model, [])
        method = "NULL"
        if support_methods:
            if period >= current_settings["user_cfg"]["work_mode_timeline"]:
                if "PSM" in support_methods:
                    method = "PSM"
                elif "POWERDOWN" in support_methods:
                    method = "POWERDOWN"
                elif "PM" in support_methods:
                    method = "PM"
            else:
                if "PM" in support_methods:
                    method = "PM"
        log.debug("__init_low_energy_method: %s" % method)
        return method

    def __read_battery(self):
        """Get battery energy & voltage"""
        if not self.__battery:
            raise TypeError("self.__battery is not registered.")

        res = {}
        # TODO: Get temperature from sensor
        self.__battery.set_temp(20)
        energy = self.__battery.get_energy()
        res = {
            "energy": energy,
            "voltage": self.__battery.get_voltage(),
        }

        return res

    def __check_battery_energy(self, energy):
        """Check battery low power alert"""
        alert_data = {}
        current_settings = settings.get()
        if current_settings["user_cfg"]["sw_low_power_alert"] is True and \
                energy <= current_settings["user_cfg"]["low_power_alert_threshold"]:
            alert_data = self.__get_alert_data(30002, {"local_time": self.__get_local_time()})

        return alert_data

    def __check_battery_low_energy_power_down(self):
        """Check battery low power power down"""
        battery_data = self.__read_battery()
        current_settings = settings.get()
        if battery_data["energy"] <= current_settings["user_cfg"]["low_power_shutdown_threshold"]:
            self.__controller.power_down()

    def __read_sensor(self):
        return {}

    def __gps_read_timeout_cb(self, args):
        self.__gps_read_break = True

    def __read_location(self):
        """Get loction info"""
        if not self.__locator:
            raise TypeError("self.__locator is not registered.")

        current_settings = settings.get()
        # Get cloud location data
        if current_settings["user_cfg"].get("loc_method"):
            cfg_loc_method = current_settings["user_cfg"].get("loc_method")
        elif current_settings["sys"]["base_cfg"]["LocConfig"]:
            cfg_loc_method = current_settings["LocConfig"]["loc_method"]
        else:
            cfg_loc_method = 7
        self.__locator_gps_hibernation_strategy(1)

        loc_gps_read_timeout = current_settings["user_cfg"]["loc_gps_read_timeout"]
        self.__gps_read_break = False
        _gps_read_timer = osTimer()
        if loc_gps_read_timeout > 0:
            timeout = 5 if loc_gps_read_timeout == 0 else loc_gps_read_timeout
            _gps_read_timer.start(timeout, 0, self.__gps_read_timeout_cb)
        while self.__gps_read_break is False:
            loc_info = self.__locator.read(cfg_loc_method)
            for k, v in loc_info.items():
                if v:
                    self.__gps_read_break = True
        _gps_read_timer.stop()
        self.__gps_read_break = False

        self.__locator_gps_hibernation_strategy(0)
        return loc_info

    def __locator_gps_hibernation_strategy(self, onoff):
        """Set GPS sleep"""
        current_settings = settings.get()
        work_cycle_period = current_settings["user_cfg"]["work_cycle_period"]
        if self.__locator.gps:
            if work_cycle_period >= 3600:
                self.__locator.gps.power_switch(onoff)
            elif 1800 <= work_cycle_period < 3600:
                self.__locator.gps.backup(onoff)
            elif 0 < work_cycle_period < 1200:
                self.__locator.gps.standby(onoff)

    def __read_cloud_location(self, loc_info):
        """Format cloud loction data by source loction info"""
        res = {}
        loc_method_dict = {v: k for k, v in _loc_method.__dict__.items()}
        for loc_method in loc_method_dict.keys():
            if loc_info.get(loc_method):
                log.debug("Location Data loc_method: %s" % loc_method_dict[loc_method])
                res = self.__get_loc_data(loc_method, loc_info[loc_method])
                break
        return res

    def __check_speed(self, gps_data):
        """Check speed by GPS location info and check whether over speed or not"""
        if not self.__locator:
            raise TypeError("self.__locator is not registered")

        current_settings = settings.get()
        alert_data = {
            "current_speed": 0.00
        }
        if current_settings["user_cfg"]["sw_over_speed_alert"] is True:
            if self.__locator.gps:
                vtg_data = self.__gps_match.GxVTG(gps_data)
                speed = self.__gps_parse.GxVTG_speed(vtg_data)
                if speed and float(speed) >= current_settings["user_cfg"]["over_speed_threshold"]:
                    alert_code = 30003
                    alert_info = {"local_time": self.__get_local_time()}
                    alert_data = self.__get_alert_data(alert_code, alert_info)
                if speed:
                    alert_data["current_speed"] = float(speed)

        log.debug("__check_speed: %s" % str(alert_data))
        return alert_data

    def __get_ali_loc_data(self, loc_method, loc_data):
        """Format aliyun loction data"""
        res = {"GeoLocation": {}}

        current_settings = settings.get()
        map_coordinate_system = current_settings["LocConfig"]["map_coordinate_system"]
        if loc_method == 0x1:
            gga_data = self.__gps_match.GxGGA(loc_data)
            data = {}
            if gga_data:
                Longtitude, Latitude, Altitude = self.__locator.gps.read_coordinates(loc_data)
                if map_coordinate_system == "GCJ02":
                    Longtitude, Latitude = self.__locator.wgs84togcj02(Longtitude, Latitude)
                if Latitude:
                    data["Latitude"] = float(Latitude)
                if Longtitude:
                    data["Longtitude"] = float(Longtitude)
                if Altitude:
                    data["Altitude"] = float(Altitude)
                if data:
                    data["CoordinateSystem"] = 1 if map_coordinate_system == "WGS84" else 2
            res = {"GeoLocation": data}
        elif loc_method in (0x2, 0x4):
            if loc_data:
                if loc_data[0]:
                    Longtitude = loc_data[0][0]
                    Latitude = loc_data[0][1]
                    if map_coordinate_system == "GCJ02":
                        Longtitude, Latitude = self.__locator.wgs84togcj02(Longtitude, Latitude)
                    res["GeoLocation"] = {
                        "Longtitude": Longtitude,
                        "Latitude": Latitude,
                        # "Altitude": 0.0,
                        "CoordinateSystem": (1 if map_coordinate_system == "WGS84" else 2)
                    }

        return res

    def __get_quec_loc_data(self, loc_method, loc_data):
        """Format queccloud loction data"""
        if loc_method == 0x1:
            res = {"gps": []}
            r = self.__gps_match.GxRMC(loc_data)
            if r:
                res["gps"].append(r)

            r = self.__gps_match.GxGGA(loc_data)
            if r:
                res["gps"].append(r)

            r = self.__gps_match.GxVTG(loc_data)
            if r:
                res["gps"].append(r)
            return res
        elif loc_method == 0x2:
            return {"non_gps": ["LBS"]}
        elif loc_method == 0x4:
            return {"non_gps": []}

    def __get_loc_data(self, loc_method, loc_data):
        """Format loction data for different cloud"""
        current_settings = settings.get()
        if current_settings["sys"]["cloud"] & SYSConfig._cloud.quecIot:
            return self.__get_quec_loc_data(loc_method, loc_data)
        elif current_settings["sys"]["cloud"] & SYSConfig._cloud.AliYun:
            return self.__get_ali_loc_data(loc_method, loc_data)

        return {}

    def __get_temp_humidity(self):
        data = {}
        if self.__temp_humidity_sensor is not None:
            on_res = self.__temp_humidity_sensor.on()
            if on_res:
                temperature, humidity = self.__temp_humidity_sensor.read()
                data["temperature"] = temperature
                data["humidity"] = humidity
                self.__temp_humidity_sensor.off()
        return data

    def add_module(self, module):
        """add modules for collecting data"""
        if isinstance(module, Controller):
            self.__controller = module
            return True
        elif isinstance(module, DeviceCheck):
            self.__devicecheck = module
            return True
        elif isinstance(module, Battery):
            self.__battery = module
            return True
        elif isinstance(module, Sensor):
            self.__sensor = module
            return True
        elif isinstance(module, Location):
            self.__locator = module
            return True
        elif isinstance(module, History):
            self.__history = module
            return True
        elif isinstance(module, TempHumiditySensor):
            self.__temp_humidity_sensor = module
            return True

        return False

    def device_status_get(self):
        """Get device status from DeviceCheck module
        Return:
        {
            "device_module_status": {
                "net": 1,
                "location": 1,
                "temp_sensor": 1,
                "light_sensor": 1,
                "move_sensor": 1,
                "mike": 1
            },
            "fault_alert": {
                "local_time": "1651136994000"
            }
        }
        """
        if not self.__devicecheck:
            raise TypeError("self.__devicecheck is not registered.")
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        device_status_data = {}
        device_module_status = {}
        alert_code = 20000

        net_status = self.__devicecheck.net()
        location_status = self.__devicecheck.location()
        self.__net_status = True if net_status == (3, 1) else False
        self.__loc_status = location_status
        temp_status = self.__devicecheck.temp()
        light_status = self.__devicecheck.light()
        triaxial_status = self.__devicecheck.triaxial()
        mike_status = self.__devicecheck.mike()

        device_module_status["net"] = 1 if net_status == (3, 1) else 0
        device_module_status["location"] = 1 if location_status else 0

        # TODO: Check Sensor.
        if temp_status is not None:
            device_module_status["temp_sensor"] = 1 if temp_status else 0
        if light_status is not None:
            device_module_status["light_sensor"] = 1 if temp_status else 0
        if triaxial_status is not None:
            device_module_status["move_sensor"] = 1 if temp_status else 0
        if mike_status is not None:
            device_module_status["mike"] = 1 if temp_status else 0

        device_status = True
        # TODO: Led Show
        if net_status == (3, 1) and location_status is True and \
                (temp_status is True or temp_status is None) and \
                (light_status is True or light_status is None) and \
                (triaxial_status is True or triaxial_status is None) and \
                (mike_status is True or mike_status is None):
            # self.__controller.running_led_show(200, 200)
            device_status = True
        else:
            # self.__controller.running_led_show(2000, 200)
            device_status = False

        if device_status is False:
            device_status_data.update(self.__get_alert_data(alert_code, {"local_time": self.__get_local_time()}))
        if net_status[0] == 1:
            device_status_data.update(self.__get_alert_data(30004, {"local_time": self.__get_local_time()}))

        device_status_data.update({"device_module_status": device_module_status})

        return device_status_data

    def device_status_check(self):
        """Check device status and publish data to cloud"""
        device_status_check_res = self.device_status_get()
        return self.device_data_report(event_data=device_status_check_res)

    def device_data_get(self, power_switch=True):
        """Get device business data
        return:
        data format:
        {
            "power_switch": True,
            "local_time": "1651136994000",
            ...
        }
        """
        current_settings = settings.get()

        device_data = {
            "power_switch": power_switch,
            "local_time": self.__get_local_time(),
            "gps_mode": current_settings["LocConfig"]["gps_mode"],
        }

        # Get ota status & drive behiver code
        device_data.update({
            "ota_status": current_settings["user_cfg"]["ota_status"],
            "drive_behavior_code": current_settings["user_cfg"]["drive_behavior_code"],
        })

        # Get user settings info
        device_data.update(current_settings["user_cfg"])

        # Format loc method
        device_data.update({"loc_method": self.__format_loc_method(current_settings["user_cfg"]["loc_method"])})

        # Get cloud location data
        if self.__loc_status:
            loc_info = self.__read_location()
            cloud_loc = self.__read_cloud_location(loc_info)
            device_data.update(cloud_loc)
            gps_data = loc_info.get(_loc_method.gps)
            if gps_data:
                gga_satellite = self.__gps_parse.GxGGA_satellite_num(self.__gps_match.GxGGA(gps_data))
                log.debug("GxGGA Satellite Num %s" % gga_satellite)
                gsv_satellite = self.__gps_parse.GxGSV_satellite_num(self.__gps_match.GxGSV(gps_data))
                log.debug("GxGSV Satellite Num %s" % gsv_satellite)
                # Get gps speed
                device_data.update(self.__check_speed(gps_data))

        # Get battery energy
        battery_data = self.__read_battery()
        device_data.update(battery_data)
        if battery_data.get("energy") is not None:
            check_battery_energy = self.__check_battery_energy(battery_data.get("energy"))
            device_data.update(check_battery_energy)

        temp_humidity_data = self.__get_temp_humidity()
        device_data.update(temp_humidity_data)

        # TODO: Add other machine info.

        return device_data

    def device_data_report(self, power_switch=True, event_data={}, msg=""):
        """Publish data to cloud from controller"""
        # TODO: msg to mark post data source
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        device_data = self.device_data_get(power_switch)
        if event_data:
            device_data.update(event_data)

        post_res = self.__controller.remote_post_data(device_data)

        # OTA status rst
        current_settings = settings.get() if self.__controller else {}
        ota_status_info = current_settings["user_cfg"]["ota_status"]
        if ota_status_info["upgrade_status"] in (3, 4):
            self.ota_status_reset()

        return post_res

    def ota_status_reset(self):
        """Reset customize ota status"""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        current_settings = settings.get()
        ota_status_info = current_settings["user_cfg"]["ota_status"]
        ota_info = {
            "sys_current_version": DEVICE_FIRMWARE_VERSION,
            "sys_target_version": "--",
            "app_current_version": PROJECT_VERSION,
            "app_target_version": "--",
            "upgrade_module": 0,
            "upgrade_status": 0,
        }
        ota_status_info.update(ota_info)
        self.__controller.settings_set("ota_status", ota_status_info)

        if current_settings["user_cfg"]["user_ota_action"] != -1:
            self.__controller.settings_set("user_ota_action", -1)
        return self.__controller.settings_save()

    def ota_status_init(self):
        """Init customize ota status"""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        try:
            current_settings = settings.get()
            ota_status = current_settings["user_cfg"]["ota_status"]
            log.debug("ota_status_init ota_status: %s" % str(ota_status))
            save_flag = False
            if ota_status["sys_target_version"] != "--":
                if ota_status["sys_target_version"] == DEVICE_FIRMWARE_VERSION:
                    if ota_status["upgrade_status"] != 3:
                        ota_status["upgrade_status"] = 3
                        save_flag = True
                else:
                    if ota_status["upgrade_status"] != 4:
                        ota_status["upgrade_status"] = 4
                        save_flag = True
            if ota_status["app_target_version"] != "--":
                if ota_status["app_target_version"] == PROJECT_VERSION:
                    if ota_status["upgrade_status"] != 3:
                        ota_status["upgrade_status"] = 3
                        save_flag = True
                else:
                    if ota_status["upgrade_status"] != 4:
                        ota_status["upgrade_status"] = 4
                        save_flag = True
            if save_flag:
                self.__controller.settings_set("ota_status", ota_status)
                self.__controller.settings_save()
        except:
            return False
        return True

    def report_history(self):
        """Publish history data to cloud."""
        if not self.__history:
            raise TypeError("self.__history is not registered.")
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        res = True
        hist = self.__history.read()
        if hist["data"]:
            pt_count = 0
            for i, data in enumerate(hist["data"]):
                pt_count += 1
                if not self.__controller.remote_post_data(data):
                    res = False
                    break

            hist["data"] = hist["data"][pt_count:]
            if hist["data"]:
                # Flush data in hist-dictionary to tracker_data.hist file.
                self.__history.write(hist["data"])

        return res

    # Do cloud event downlink option by controller
    def event_option(self, *args, **kwargs):
        # TODO: Data Type Passthrough (Not Support Now).
        pass

    def event_done(self, *args, **kwargs):
        """Hanle setting object model downlink message from cloud."""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        try:
            setting_flag = 0

            for arg in args:
                log.debug("arg: %s" % str(arg))
                if hasattr(UserConfig, arg[0]):
                    log.debug("UserConfig %s" % arg[0])
                    if arg[0] not in ("ota_status", "loc_method", "user_ota_action"):
                        set_res = self.__controller.settings_set(arg[0], arg[1])
                        if set_res and setting_flag == 0:
                            setting_flag = 1
                if hasattr(self, arg[0]):
                    getattr(self, arg[0])(arg[1])
                    if arg[0] in ("ota_status", "loc_method", "user_ota_action") and setting_flag == 0:
                        setting_flag = 1

            if setting_flag:
                self.__controller.settings_save()
            return True
        except:
            return False

    def event_query(self, *args, **kwargs):
        """Hanle quering object model downlink message from cloud."""
        power_switch = kwargs.get("power_switch", 1)
        power_switch = bool(power_switch)
        return self.device_data_report(power_switch=power_switch)

    def event_ota_plain(self, *args, **kwargs):
        """Hanle OTA plain from cloud."""
        log.debug("ota_plain args: %s, kwargs: %s" % (str(args), str(kwargs)))
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        current_settings = settings.get()
        if current_settings["user_cfg"]["sw_ota"]:
            if current_settings["user_cfg"]["sw_ota_auto_upgrade"] or current_settings["user_cfg"]["user_ota_action"] != -1:
                if current_settings["user_cfg"]["sw_ota_auto_upgrade"]:
                    ota_action_val = 1
                else:
                    if current_settings["user_cfg"]["user_ota_action"] != -1:
                        ota_action_val = current_settings["user_cfg"]["user_ota_action"]
                    else:
                        return

                if current_settings["sys"]["cloud"] == SYSConfig._cloud.quecIot:
                    if args and args[0]:
                        if args[0][0] == "ota_cfg":
                            module = args[0][1].get("componentNo")
                            target_version = args[0][1].get("targetVersion")
                            upgrade_module = 1 if module == DEVICE_FIRMWARE_NAME else 2
                            source_version = DEVICE_FIRMWARE_VERSION if module == DEVICE_FIRMWARE_NAME else PROJECT_VERSION
                            if current_settings['user_cfg']['ota_status']['upgrade_module'] == upgrade_module and \
                                    current_settings['user_cfg']['ota_status']['upgrade_status'] <= 1 and \
                                    target_version != source_version:
                                self.__controller.remote_ota_action(action=ota_action_val, module=module)
                elif current_settings["sys"]["cloud"] == SYSConfig._cloud.AliYun:
                    if args and args[0]:
                        if args[0][0] == "ota_cfg":
                            module = args[0][1].get("module")
                            target_version = args[0][1].get("version")
                            upgrade_module = 1 if module == DEVICE_FIRMWARE_NAME else 2
                            source_version = DEVICE_FIRMWARE_VERSION if module == DEVICE_FIRMWARE_NAME else PROJECT_VERSION
                            if current_settings['user_cfg']['ota_status']['upgrade_module'] == upgrade_module and \
                                    current_settings['user_cfg']['ota_status']['upgrade_status'] <= 1 and \
                                    target_version != source_version:
                                self.__controller.remote_ota_action(action=ota_action_val, module=module)
                else:
                    log.error("Current Cloud (0x%X) Not Supported!" % current_settings["sys"]["cloud"])
        else:
            if current_settings["sys"]["cloud"] == SYSConfig._cloud.quecIot:
                if args and args[0]:
                    if args[0][0] == "ota_cfg":
                        module = args[0][1].get("componentNo")
                        self.__controller.remote_ota_action(action=0, module=module)
            elif current_settings["sys"]["cloud"] == SYSConfig._cloud.AliYun:
                if args and args[0]:
                    if args[0][0] == "ota_cfg":
                        module = args[0][1].get("module")
                        self.__controller.remote_ota_action(action=0, module=module)
            else:
                log.error("Current Cloud (0x%X) Not Supported!" % current_settings["sys"]["cloud"])

    def event_ota_file_download(self, *args, **kwargs):
        # OAT MQTT File Download Is Not Supported Yet.
        pass

    def rrpc_request(self, *args, **kwargs):
        """Hanle RRPC request"""
        message_id = kwargs["message_id"]
        data = kwargs["data"]
        log.debug("RRPC message_id: %s" % message_id)
        log.debug("RRPC data: %s" % data)
        self.__controller.remote_rrpc_response(message_id, data)

    def power_switch(self, onoff=1):
        """Control device power"""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        onoff = bool(onoff)
        self.event_query(power_switch=onoff)
        if onoff is False:
            self.__controller.power_down()

    def user_ota_action(self, action):
        """Set user set ota action"""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        current_settings = settings.get()
        if current_settings["user_cfg"]["sw_ota"] and current_settings["user_cfg"]["sw_ota_auto_upgrade"] is False:
            ota_status_info = current_settings["user_cfg"]["ota_status"]
            if ota_status_info["upgrade_status"] == 1 and current_settings["user_cfg"]["user_ota_action"] == -1:
                self.__controller.settings_set("user_ota_action", action)
                self.__controller.settings_save()
                self.__controller.remote_ota_check()

    def ota_status(self, upgrade_info=None):
        """Set ota status by ota upgrade process"""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        try:
            current_settings = settings.get()
            if upgrade_info and current_settings["user_cfg"]["sw_ota"]:
                ota_status_info = current_settings["user_cfg"]["ota_status"]
                ota_info = {}
                pass_flag = False
                if ota_status_info["sys_target_version"] == "--" and ota_status_info["app_target_version"] == "--":
                    if upgrade_info[0] == DEVICE_FIRMWARE_NAME:
                        if upgrade_info[2] != DEVICE_FIRMWARE_VERSION:
                            ota_info["upgrade_module"] = 1
                            ota_info["sys_target_version"] = upgrade_info[2]
                        else:
                            pass_flag = True
                    elif upgrade_info[0] == PROJECT_NAME:
                        if upgrade_info[2] != PROJECT_VERSION:
                            ota_info["upgrade_module"] = 2
                            ota_info["app_target_version"] = upgrade_info[2]
                        else:
                            pass_flag = True
                if pass_flag is False:
                    ota_info["upgrade_status"] = upgrade_info[1]
                ota_status_info.update(ota_info)
                self.__controller.settings_set("ota_status", ota_status_info)
                self.__controller.settings_save()
        except:
            return False
        return True

    def loc_method(self, method):
        """Set loc_method from cloud downlink message."""
        log.debug("loc_method: %s" % str(method))
        current_settings = settings.get()
        v = '0b'
        if current_settings["sys"]["cloud"] == SYSConfig._cloud.quecIot:
            v += str(int(method.get(3, 0)))
            v += str(int(method.get(2, 0)))
            v += str(int(method.get(1, 0)))
        elif current_settings["sys"]["cloud"] == SYSConfig._cloud.AliYun:
            v += str(int(method.get("wifi", 0)))
            v += str(int(method.get("cell", 0)))
            v += str(int(method.get("gps", 0)))
        value = int(v, 2)
        log.debug("loc_method value: %s" % value)
        return self.__controller.settings_set("loc_method", value)

    def power_restart(self, flag):
        """Control power restart"""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.event_query(power_switch=False)
        self.__controller.power_restart()

    def work_cycle_period(self, period):
        """Reset low energy when reset work_cycle_period."""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        try:
            self.__controller.low_energy_stop()

            self.__controller.low_energy_set_period(period)
            method = self.__init_low_energy_method(period)
            self.__controller.low_energy_set_method(method)

            self.__controller.low_energy_init()
            self.__controller.low_energy_start()
        except:
            return False
        return True

    def low_engery_option(self, low_energy_method):
        """Business option after low energy waking up."""
        log.debug("start low_engery_option")
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.report_history()
        report_flag = True
        current_settings = settings.get()
        if current_settings["user_cfg"]["work_mode"] == UserConfig._work_mode.intelligent:
            # TODO: Check speed by sensor
            if self.__loc_status:
                loc_info = self.__read_location()
                gps_data = loc_info.get(_loc_method.gps)
                speed_info = self.__check_speed(gps_data)
                if speed_info.get("current_speed") <= 0:
                    report_flag = False

        if report_flag is True:
            self.device_status_check()
            if self.__net_status:
                self.__controller.remote_device_report()
                self.__controller.remote_ota_check()

        # Check battery low enery power down.
        self.__check_battery_low_energy_power_down()

        self.__controller.low_energy_start()

        if low_energy_method == "POWERDOWN":
            self.__controller.power_down()
        log.debug("end low_engery_option")

    def thing_services(self, data):
        log.debug("thing_services data: %s" % str(data))
        service_data = {
            data["service"]: {
                "id": data["data"]["id"],
                "code": 200,
                "message": "Success",
                "data": {}
            }
        }
        self.__controller.remote_post_data(service_data)

    def update(self, observable, *args, **kwargs):
        """Observer update option"""
        if isinstance(observable, LowEnergyManage):
            log.debug("Low Energy RTC Method: %s" % args[1])
            self.low_engery_option(args[1])
