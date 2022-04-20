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

from usr.modules.sensor import Sensor
from usr.modules.battery import Battery
from usr.modules.history import History
from usr.modules.logging import getLogger
from usr.modules.mpower import LowEnergyManage
from usr.modules.common import Singleton, LOWENERGYMAP
from usr.modules.location import Location, GPSMatch, GPSParse, _loc_method
from usr.settings import PROJECT_NAME, DEVICE_FIRMWARE_NAME, settings, UserConfig, SYSConfig
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
    def __init__(self):
        self.__controller = None
        self.__devicecheck = None
        self.__battery = None
        self.__sensor = None
        self.__locator = None
        self.__history = None
        self.__gps_match = GPSMatch()
        self.__gps_parse = GPSParse()

    def __format_loc_method(self, data):
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
        return str(utime.mktime(utime.localtime()) * 1000)

    def __get_alert_data(self, alert_code, alert_info):
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
        current_settings = settings.get()
        device_model = modem.getDevModel()
        support_methds = LOWENERGYMAP.get(device_model, [])
        method = "NULL"
        if support_methds:
            if period >= current_settings["user_cfg"]["work_mode_timeline"]:
                if "PSM" in support_methds:
                    method = "PSM"
                elif "POWERDOWN" in support_methds:
                    method = "POWERDOWN"
                elif "PM" in support_methds:
                    method = "PM"
            else:
                if "PM" in support_methds:
                    method = "PM"
        log.debug("__init_low_energy_method: %s" % method)
        return method

    def __read_battery(self):
        if not self.__battery:
            raise TypeError("self.__battery is not registered.")

        res = {}
        self.__battery.set_temp(20)
        energy = self.__battery.get_energy()
        res = {
            "energy": energy,
            "voltage": self.__battery.get_voltage(),
        }

        return res

    def __check_battery_energy(self, energy):
        alert_data = {}
        current_settings = settings.get()
        if energy <= current_settings["user_cfg"]["low_power_alert_threshold"]:
            alert_data = self.__get_alert_data(30002, {"local_time": self.__get_local_time()})

        return alert_data

    def __read_sensor(self):
        return {}

    def __read_location(self):
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
        loc_info = self.__locator.read(cfg_loc_method)
        return loc_info

    def __read_cloud_location(self, loc_info):
        res = {}
        loc_method_dict = {v: k for k, v in _loc_method.__dict__.items()}
        for loc_method in loc_method_dict.keys():
            if loc_info.get(loc_method):
                log.debug("Location Data loc_method: %s" % loc_method_dict[loc_method])
                res = self.__get_loc_data(loc_method, loc_info[loc_method])
                break
        return res

    def __check_speed(self, gps_data):
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
        res = {"GeoLocation": {}}

        if loc_method == 0x1:
            gga_data = self.__gps_match.GxGGA(loc_data)
            data = {}
            if gga_data:
                Latitude = self.__gps_parse.GxGGA_latitude(gga_data)
                if Latitude:
                    data["Latitude"] = float("%.2f" % float(Latitude))
                Longtitude = self.__gps_parse.GxGGA_longtitude(gga_data)
                if Longtitude:
                    data["Longtitude"] = float("%.2f" % float(Longtitude))
                Altitude = self.__gps_parse.GxGGA_altitude(gga_data)
                if Altitude:
                    data["Altitude"] = float("%.2f" % float(Altitude))
                if data:
                    data["CoordinateSystem"] = 1
            res = {"GeoLocation": data}
        elif loc_method in (0x2, 0x4):
            if loc_data:
                res["GeoLocation"] = {
                    "Longtitude": round(loc_data[0], 2),
                    "Latitude": round(loc_data[1], 2),
                    # "Altitude": 0.0,
                    "CoordinateSystem": 1
                }

        return res

    def __get_quec_loc_data(self, loc_method, loc_data):
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
        current_settings = settings.get()
        if current_settings["sys"]["cloud"] & SYSConfig._cloud.quecIot:
            return self.__get_quec_loc_data(loc_method, loc_data)
        elif current_settings["sys"]["cloud"] & SYSConfig._cloud.AliYun:
            return self.__get_ali_loc_data(loc_method, loc_data)

        return {}

    def add_module(self, module):
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

        return False

    def device_status_get(self):
        if not self.__devicecheck:
            raise TypeError("self.__devicecheck is not registered.")
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        device_status_data = {}
        device_module_status = {}
        alert_code = 20000

        net_status = self.__devicecheck.net()
        location_status = self.__devicecheck.location()
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
            # self.__controller.running_led_show(0.5)
            device_status = True
        else:
            # self.__controller.running_led_show(2)
            device_status = False

        if device_status is False:
            device_status_data = self.__get_alert_data(alert_code, {"local_time": self.__get_local_time()})

        device_status_data.update({"device_module_status": device_module_status})

        return device_status_data

    def device_status_check(self):
        device_status_check_res = self.device_status_get()
        self.device_data_report(event_data=device_status_check_res)

    def device_data_get(self, power_switch=True):
        current_settings = settings.get()

        device_data = {
            "power_switch": power_switch,
            "local_time": self.__get_local_time(),
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

        # TODO: Add other machine info.

        return device_data

    def device_data_report(self, power_switch=True, event_data={}, msg=""):
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
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        current_settings = settings.get()
        ota_status_info = current_settings["user_cfg"]["ota_status"]
        ota_info = {}
        ota_info["sys_target_version"] = "--"
        ota_info["app_target_version"] = "--"
        ota_info["upgrade_module"] = 0
        ota_info["upgrade_status"] = 0
        ota_status_info.update(ota_info)
        self.__controller.settings_set("ota_status", ota_status_info)

        if current_settings["user_cfg"]["user_ota_action"] != -1:
            self.__controller.settings_set("user_ota_action", -1)

    def report_history(self):
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
        return False

    def event_done(self, *args, **kwargs):
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        try:
            setting_flag = 0

            for arg in args:
                if hasattr(UserConfig, arg[0]):
                    set_res = self.__controller.settings_set(arg[0], arg[1])
                    if set_res and setting_flag == 0:
                        setting_flag = 1
                if hasattr(self, arg[0]):
                    getattr(self, arg[0])(arg[1])

            if setting_flag:
                self.__controller.settings_save()
            return True
        except:
            return False

    def event_query(self, *args, **kwargs):
        return self.device_data_report()

    def event_ota_plain(self, *args, **kwargs):
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

                if current_settings["sys"]["cloud"] == SYSConfig._cloud.quecIot or \
                        current_settings["sys"]["cloud"] == SYSConfig._cloud.AliYun:
                    log.debug("ota_plain args: %s, kwargs: %s" % (str(args), str(kwargs)))
                    self.__controller.remote_ota_action(action=ota_action_val, module=kwargs.get("module"))
                else:
                    log.error("Current Cloud (0x%X) Not Supported!" % current_settings["sys"]["cloud"])

    def event_ota_file_download(self, *args, **kwargs):
        # OAT MQTT File Download Is Not Supported Yet.
        return False

    def power_switch(self, flag=None):
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.event_query(power_switch=flag)
        if flag is False:
            self.__controller.power_down()

    def user_ota_action(self, action):
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
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        current_settings = settings.get()
        if upgrade_info and current_settings["user_cfg"]["sw_ota"]:
            ota_status_info = current_settings["user_cfg"]["ota_status"]
            if ota_status_info["sys_target_version"] == "--" and ota_status_info["app_target_version"] == "--":
                ota_info = {}
                if upgrade_info[0] == DEVICE_FIRMWARE_NAME:
                    ota_info["upgrade_module"] = 1
                    ota_info["sys_target_version"] = upgrade_info[2]
                elif upgrade_info[0] == PROJECT_NAME:
                    ota_info["upgrade_module"] = 2
                    ota_info["app_target_version"] = upgrade_info[2]
                ota_info["upgrade_status"] = upgrade_info[1]
                ota_status_info.update(ota_info)
                self.__controller.settings_set("ota_status", ota_status_info)
                self.__controller.settings_save()

    def power_restart(self, flag):
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.event_query(power_switch=False)
        self.__controller.power_restart()

    def work_cycle_period(self, period):
        # Reset work_cycle_period & Reset RTC
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.__controller.low_energy_stop()

        self.__controller.low_energy_set_period(period)
        method = self.__init_low_energy_method(period)
        self.__controller.low_energy_set_method(method)

        self.__controller.low_energy_init()
        self.__controller.low_energy_start()

    def cloud_init_params(self, params):
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.__controller.settings_set("cloud", params)
        self.__controller.settings_save()

    def low_engery_option(self, low_energy_method):
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.report_history()
        current_settings = settings.get()
        if current_settings["user_cfg"]["work_mode"] == UserConfig._work_mode.intelligent:
            speed_info = self.__check_speed()
            if speed_info.get("current_speed") > 0:
                self.device_data_report()
        else:
            self.device_data_report()

        self.__controller.low_energy_start()

        if low_energy_method == "PSM":
            # TODO: PSM option.
            pass
        elif low_energy_method == "POWERDOWN":
            self.__controller.power_down()

    def update(self, observable, *args, **kwargs):
        if isinstance(observable, LowEnergyManage):
            log.debug("Low Energy RTC Method: %s" % args[1])
            self.low_engery_option(args[1])
