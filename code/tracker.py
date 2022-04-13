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

import sim
import utime
import modem
import _thread
import checkNet
import dataCall

from misc import Power

from usr.led import LED
from usr.sensor import Sensor
from usr.battery import Battery
from usr.ota import OTAFileClear
from usr.history import History
from usr.logging import getLogger
from usr.mpower import LowEnergyRTC
from usr.remote import RemotePublish, RemoteSubcribe
from usr.aliyunIot import AliYunIot, AliObjectModel
from usr.quecthing import QuecThing, QuecObjectModel
from usr.common import numiter, Singleton
from usr.location import Location, GPSMatch, GPSParse
from usr.settings import ALERTCODE, LOWENERGYMAP, PROJECT_NAME, PROJECT_VERSION, \
    DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION, settings, default_values_app, \
    default_values_sys, Settings, quec_object_model, ali_object_model

try:
    from misc import USB
except ImportError:
    USB = None
try:
    from misc import PowerKey
except ImportError:
    PowerKey = None


log = getLogger(__name__)

sim.setSimDet(1, 0)


def pwk_callback(status):
    if status == 0:
        log.info("PowerKey Release.")
    elif status == 1:
        log.info("PowerKey Press.")
    else:
        log.warn("Unknown PowerKey Status:", status)


def usb_callback(status):
    if status == 0:
        log.info("USB is disconnected.")
    elif status == 1:
        log.info("USB is connected.")
    else:
        log.warn("Unknown USB Stauts:", status)


def nw_callback(args):
    net_check_res = DeviceCheck().net()
    if args[1] != 1:
        if net_check_res[0] == 1 and net_check_res[1] != 1:
            log.warn("SIM abnormal!")
            alert_code = 30004
            alert_info = {"local_time": Collector().__get_local_time()}
            alert_data = Collector().__get_alert_data(alert_code, alert_info)
            Controller().device_data_report(event_data=alert_data, msg="sim_abnormal")
    else:
        if net_check_res == (3, 1):
            pass


class Collector(Singleton):
    def __init__(self):
        self.__controller = None
        self.__devicecheck = None
        self.__battery = None
        self.__sensor = None
        self.__locator = None
        self.__history = None
        self.cloud_om = None

        self.num_iter = numiter()
        self.num_lock = _thread.allocate_lock()

    def __get_num(self):
        with self.num_lock:
            try:
                num = next(self.num_iter)
            except StopIteration:
                self.num_iter = numiter()
                num = next(self.num_iter)

        return str(num)

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

    def __device_speed_check(self):
        current_settings = self.__controller.settings_get() if self.__controller else {}
        alert_data = {
            "current_speed": 0.00
        }
        if current_settings["app"]["sw_over_speed_alert"] is True:
            if self.__locator.gps:
                gps_data = self.__locator.gps.read()[1]
                gps_match = GPSMatch()
                gps_parse = GPSParse()
                vtg_data = gps_match.GxVTG(gps_data)
                speed = gps_parse.GxVTG_speed(vtg_data)
                if speed and float(speed) >= current_settings["app"]["over_speed_threshold"]:
                    alert_code = 30003
                    alert_info = {"local_time": self.__get_local_time()}
                    alert_data = self.__get_alert_data(alert_code, alert_info)
                if speed:
                    alert_data["current_speed"] = float(speed)

        return alert_data

    def __get_local_time(self):
        return str(utime.mktime(utime.localtime()) * 1000)

    def __get_alert_data(self, alert_code, alert_info):
        current_settings = self.__controller.settings_get() if self.__controller else {}
        alert_data = {}
        if ALERTCODE.get(alert_code):
            alert_status = current_settings.get("app", {}).get("sw_" + ALERTCODE.get(alert_code))
            if alert_status:
                alert_data = {ALERTCODE.get(alert_code): alert_info}
            else:
                log.warn("%s switch is %s" % (ALERTCODE.get(alert_code), alert_status))
        else:
            log.error("altercode (%s) is not exists. alert info: %s" % (alert_code, alert_info))

        return alert_data

    def __get_low_energy_method(self, period):
        current_settings = self.__controller.settings_get()
        device_model = modem.getDevModel()
        support_methds = LOWENERGYMAP.get(device_model, [])
        method = "NULL"
        if support_methds:
            if period >= current_settings["sys"]["work_mode_timeline"]:
                if "PSM" in support_methds:
                    method = "PSM"
                elif "POWERDOWN" in support_methds:
                    method = "POWERDOWN"
                elif "PM" in support_methds:
                    method = "PM"
            else:
                if "PM" in support_methds:
                    method = "PM"
        log.debug("__get_low_energy_method: %s" % method)
        return method

    def __get_ali_loc_data(self, loc_method, loc_data):
        res = {"GeoLocation": {}}

        if loc_method == 0x1:
            gps_match = GPSMatch()
            gps_parse = GPSParse()
            gga_data = gps_match.GxGGA(loc_data)
            data = {}
            if gga_data:
                Latitude = gps_parse.GxGGA_latitude(gga_data)
                if Latitude:
                    data["Latitude"] = float("%.2f" % float(Latitude))
                Longtitude = gps_parse.GxGGA_longtitude(gga_data)
                if Longtitude:
                    data["Longtitude"] = float("%.2f" % float(Longtitude))
                Altitude = gps_parse.GxGGA_altitude(gga_data)
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
            gps_match = GPSMatch()
            r = gps_match.GxRMC(loc_data)
            if r:
                res["gps"].append(r)

            r = gps_match.GxGGA(loc_data)
            if r:
                res["gps"].append(r)

            r = gps_match.GxVTG(loc_data)
            if r:
                res["gps"].append(r)
            return res
        elif loc_method == 0x2:
            return {"non_gps": ["LBS"]}
        elif loc_method == 0x4:
            return {"non_gps": []}

    def init_cloud_object_module(self, cloud_object_model):
        for om_type in cloud_object_model.keys():
            for om_key in cloud_object_model[om_type]:
                om_key_id = cloud_object_model[om_type][om_key].get("id")
                om_key_perm = cloud_object_model[om_type][om_key].get("perm")
                self.cloud_om.set_item(om_type, om_key, om_key_id, om_key_perm)
                om_key_struct = cloud_object_model[om_type][om_key].get("struct_info", {})
                for struct_key in om_key_struct.keys():
                    self.cloud_om.set_item_struct(
                        om_type, om_key, struct_key, struct_key_id=om_key_struct[struct_key].get("id"),
                        struct_key_struct=om_key_struct[struct_key].get("struct_info")
                    )

    def set_controller(self, controller):
        if isinstance(controller, Controller):
            self.__controller = controller
            return True
        return False

    def set_devicecheck(self, devicecheck):
        if isinstance(devicecheck, DeviceCheck):
            self.__devicecheck = devicecheck
            return True
        return False

    def set_battery(self, battery):
        if isinstance(battery, Battery):
            self.__battery = battery
            return True
        return False

    def set_sensor(self, sensor):
        if isinstance(sensor, Sensor):
            self.__sensor = sensor
            return True
        return False

    def set_locator(self, locator):
        if isinstance(locator, Location):
            self.__locator = locator
            return True
        return False

    def set_cloud_om(self, cloud_om):
        if isinstance(cloud_om, QuecObjectModel) or isinstance(cloud_om, AliObjectModel):
            self.cloud_om = cloud_om
            return True
        return False

    def set_history(self, history):
        if isinstance(history, History):
            self.__history = history
            return True
        return False

    def get_loc_data(self, loc_method, loc_data):
        current_settings = self.__controller.settings_get()
        if current_settings["sys"]["cloud"] & default_values_sys._cloud.quecIot:
            return self.__get_quec_loc_data(loc_method, loc_data)
        elif current_settings["sys"]["cloud"] & default_values_sys._cloud.AliYun:
            return self.__get_ali_loc_data(loc_method, loc_data)
        return {}

    def device_status_get(self):
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
            self.__controller.running_led_show(0.5)
        else:
            self.__controller.running_led_show(2)
            device_status = False

        if device_status is False:
            device_status_data = self.__get_alert_data(alert_code, {"local_time": self.__get_local_time()})

        device_status_data.update({"device_module_status": device_module_status})

        return device_status_data

    def device_status_check(self):
        device_status_check_res = self.device_status_get()
        self.device_data_report(event_data=device_status_check_res)

    def device_data_get(self, power_switch=True):
        current_settings = self.__controller.settings_get() if self.__controller else {}

        device_data = {
            "power_switch": power_switch,
            "local_time": self.__get_local_time(),
        }

        # Get cloud location data
        loc_info = self.__locator.read(current_settings["app"]["loc_method"]) if self.__locator else None
        if loc_info:
            loc_method_dict = {1: "GPS", 2: "CELL", 4: "WIFI"}
            loc_data = None
            for loc_method in loc_method_dict.keys():
                if loc_info.get(loc_method):
                    log.debug("Location Data loc_method: %s" % loc_method_dict[loc_method])
                    loc_data = loc_info[loc_method]
                    break
            if loc_data:
                report_loc_data = None
                if current_settings["sys"]["cloud"] & default_values_sys._cloud.quecIot:
                    report_loc_data = self.__get_quec_loc_data(loc_method, loc_data)
                elif current_settings["sys"]["cloud"] & default_values_sys._cloud.AliYun:
                    report_loc_data = self.__get_ali_loc_data(loc_method, loc_data)
                if report_loc_data:
                    device_data.update(report_loc_data)

        # Get gps speed
        over_speed_check_res = self.__device_speed_check()
        log.debug("over_speed_check_res: %s" % str(over_speed_check_res))
        device_data.update(over_speed_check_res)

        # Get battery energy
        energy = self.__battery.get_energy()
        device_data.update({
            "energy": energy,
            "voltage": self.__battery.get_voltage(),
        })
        if energy <= current_settings["app"]["low_power_alert_threshold"]:
            alert_data = self.__get_alert_data(30002, {"local_time": self.__get_local_time()})
            device_data.update(alert_data)

        # Get ota status & drive behiver code
        device_data.update({
            "ota_status": current_settings["sys"]["ota_status"],
            "drive_behavior_code": current_settings["sys"]["drive_behavior_code"],
        })

        # Get app settings info
        device_data.update(current_settings["app"])

        # Format loc method
        device_data.update({"loc_method": self.__format_loc_method(current_settings["app"]["loc_method"])})

        # TODO: Add other machine info.

        return device_data

    def device_data_report(self, power_switch=True, event_data={}, msg=""):
        device_data = self.device_data_get(power_switch)
        if event_data:
            device_data.update(event_data)

        num = self.__get_num()
        topic = num + "/" + msg if msg else num
        log.debug("[x] post data topic [%s]" % topic)
        post_res = self.__controller.remote_post_data(device_data)

        # OTA status rst
        current_settings = settings.get()
        ota_status_info = current_settings["sys"]["ota_status"]
        if ota_status_info["upgrade_status"] in (3, 4):
            self.ota_status_reset()

        return post_res

    def ota_status_reset(self):
        current_settings = self.__controller.get()
        ota_status_info = current_settings["sys"]["ota_status"]
        ota_info = {}
        ota_info["sys_target_version"] = "--"
        ota_info["app_target_version"] = "--"
        ota_info["upgrade_module"] = 0
        ota_info["upgrade_status"] = 0
        ota_status_info.update(ota_info)
        self.__controller.settings_set("ota_status", ota_status_info)

        if current_settings["sys"]["user_ota_action"] != -1:
            self.__controller.settings_set("user_ota_action", -1)

    def report_history(self):
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
        try:
            setting_flag = 0

            for arg in args:
                if hasattr(default_values_app, arg[0]):
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
        current_settings = settings.get()
        if current_settings["app"]["sw_ota"]:
            if current_settings["app"]["sw_ota_auto_upgrade"] or current_settings["sys"]["user_ota_action"] != -1:
                if current_settings["app"]["sw_ota_auto_upgrade"]:
                    ota_action_val = 1
                else:
                    if current_settings["sys"]["user_ota_action"] != -1:
                        ota_action_val = current_settings["sys"]["user_ota_action"]
                    else:
                        return

                if current_settings["sys"]["cloud"] == default_values_sys._cloud.quecIot or \
                        current_settings["sys"]["cloud"] == default_values_sys._cloud.AliYun:
                    log.debug("ota_plain args: %s, kwargs: %s" % (str(args), str(kwargs)))
                    self.__controller.remote_ota_action(action=ota_action_val, module=kwargs.get("module"))
                else:
                    log.error("Current Cloud (0x%X) Not Supported!" % current_settings["sys"]["cloud"])

    def event_ota_file_download(self, *args, **kwargs):
        # OAT MQTT File Download Is Not Supported Yet.
        return False

    def power_switch(self, flag=None):
        self.event_query(power_switch=flag)
        if flag is False:
            self.__controller.power_down()

    def user_ota_action(self, action):
        current_settings = self.__controller.settings_get()
        if current_settings["app"]["sw_ota"] and current_settings["app"]["sw_ota_auto_upgrade"] is False:
            ota_status_info = current_settings["sys"]["ota_status"]
            if ota_status_info["upgrade_status"] == 1 and current_settings["sys"]["user_ota_action"] == -1:
                self.__controller.settings_set("user_ota_action", action)
                self.__controller.settings_save()
                self.__controller.remote_ota_check()

    def ota_status(self, upgrade_info=None):
        current_settings = self.__controller.settings_get()
        if upgrade_info and current_settings["app"]["sw_ota"]:
            ota_status_info = current_settings["sys"]["ota_status"]
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
        self.event_query(power_switch=False)
        self.__controller.power_restart()

    def work_cycle_period(self, period):
        # Reset work_cycle_period & Reset RTC
        self.__controller.low_energy_rtc_enable(0)

        self.__controller.low_energy_rtc_set_period(period)
        method = self.__get_low_energy_method(period)
        self.__controller.low_energy_rtc_set_method(method)

        self.__controller.low_energy_rtc_init()
        self.__controller.low_energy_rtc_start()

    def cloud_init_params(self, params):
        self.__controller.settings_set("cloud_init_params", params)
        self.__controller.settings_save()

    def low_engery_rtc_option(self, low_energy_method):
        self.report_history()
        current_settings = self.__controller.settings_get()
        if current_settings["app"]["work_mode"] == default_values_app._work_mode.intelligent:
            speed_info = self.__device_speed_check()
            if speed_info.get("current_speed") > 0:
                self.device_data_report()
        else:
            self.device_data_report()

        self.__controller.low_energy_rtc_start()

        if low_energy_method == "PSM":
            # TODO: PSM option.
            pass
        elif low_energy_method == "POWERDOWN":
            self.__controller.power_down()

    def update(self, observable, *args, **kwargs):
        if isinstance(observable, LowEnergyRTC):
            log.debug("Low Energy RTC Method: %s" % args[1])
            self.low_engery_rtc_option(args[1])


class DeviceCheck(object):

    def __init__(self):
        self.__locator = None

    def set_locator(self, locator):
        if isinstance(locator, Location):
            self.__locator = locator
            return True
        return False

    def net(self):
        current_settings = settings.get()
        checknet = checkNet.CheckNetwork(PROJECT_NAME, PROJECT_VERSION)
        timeout = current_settings.get("sys", {}).get("checknet_timeout", 60)
        check_res = checknet.wait_network_connected(timeout)
        log.debug("DeviceCheck.net res: %s" % str(check_res))
        return check_res

    def location(self):
        # return True if OK
        current_settings = settings.get()
        retry = 0
        gps_data = None
        sleep_time = 1

        while retry < 5:
            gps_data = self.__locator.read(current_settings["app"]["loc_method"])
            if gps_data:
                break
            else:
                retry += 1
                utime.sleep(sleep_time)
                sleep_time *= 2

        if gps_data:
            return True

        return False

    def temp(self):
        # return True if OK
        return None

    def light(self):
        # return True if OK
        return None

    def triaxial(self):
        # return True if OK
        return None

    def mike(self):
        # return True if OK
        return None


class Controller(Singleton):
    def __init__(self):
        self.__remote_pub = None
        self.__settings = None
        self.__low_energy_rtc = None
        self.__energy_led = None
        self.__running_led = None
        self.__power_key = None
        self.__usb = None
        self.__data_call = None
        self.__ota_file_clear = None

    def set_remote_pub(self, remote_pub):
        if isinstance(remote_pub, RemotePublish):
            self.__remote_pub = remote_pub
            return True
        return False

    def set_settings(self, settings):
        if isinstance(settings, Settings):
            self.__settings = settings
            return True
        return False

    def set_low_energy_rtc(self, low_energy_rtc):
        if isinstance(low_energy_rtc, LowEnergyRTC):
            self.__low_energy_rtc = low_energy_rtc
            return True
        return False

    def set_energy_led(self, energy_led):
        if isinstance(energy_led, LED):
            self.__energy_led = energy_led
            return True
        return False

    def set_running_led(self, running_led):
        if isinstance(running_led, LED):
            self.__running_led = running_led
            return True
        return False

    def set_power_key(self, power_key, power_key_cb):
        if isinstance(power_key, PowerKey):
            self.__power_key = power_key
            if power_key_cb:
                self.__power_key.powerKeyEventRegister(power_key_cb)
            return True
        return False

    def set_usb(self, usb, usb_cb):
        if isinstance(usb, USB):
            self.__usb = usb
            if usb_cb:
                self.__usb.setCallback(usb_cb)
            return True
        return False

    def set_data_call(self, data_call, data_call_cb):
        if data_call is dataCall:
            self.__data_call = data_call
            if data_call_cb:
                self.__data_call.setCallback(data_call_cb)
            return True
        return False

    def set_ota_file_clear(self, ota_file_clear):
        if isinstance(ota_file_clear, OTAFileClear):
            self.__ota_file_clear = ota_file_clear
            return True
        return False

    def settings_get(self):
        return self.__settings.get()

    def settings_set(self, key, value):
        if key == "loc_method":
            v = "0b"
            v += str(int(value.get(3, 0)))
            v += str(int(value.get(2, 0)))
            v += str(int(value.get(1, 0)))
            value = int(v, 2)
        set_res = self.__settings.set(key, value)
        log.debug("__settings_set key: %s, val: %s, set_res: %s" % (key, value, set_res))
        return set_res

    def settings_save(self):
        return self.__settings.save()

    def power_restart(self):
        Power.powerRestart()

    def power_down(self):
        Power.powerDown()

    def remote_post_data(self, data):
        return self.__remote_pub.post_data(data)

    def remote_ota_check(self):
        return self.__remote_pub.cloud_ota_check()

    def remote_ota_action(self, action, module):
        return self.__remote_pub.cloud_ota_action(action, module)

    def low_energy_rtc_init(self):
        return self.__low_energy_rtc.low_energy_init()

    def low_energy_rtc_start(self):
        return self.__low_energy_rtc.start_rtc()

    def low_energy_rtc_enable(self, enable):
        return self.__low_energy_rtc.enable_alarm(enable)

    def low_energy_rtc_set_period(self, period):
        return self.__low_energy_rtc.set_period(period)

    def low_energy_rtc_set_method(self, method):
        return self.__low_energy_rtc.set_low_energy_method(method)

    def ota_file_clean(self):
        self.__ota_file_clear.file_clear()

    def running_led_show(self, period):
        if self.__running_led:
            self.__running_led.set_period(period)
            return self.__running_led.led_timer_start()
        return False

    def energy_led_show(self, period):
        if self.__energy_led:
            self.__energy_led.set_period(period)
            return self.__energy_led.led_timer_start()
        return False


def tracker_main():
    current_settings = settings.get()

    collector = Collector()
    controller = Controller()
    devicecheck = DeviceCheck()
    battery = Battery()
    sensor = Sensor()
    locator = Location(current_settings["sys"]["gps_mode"], current_settings["sys"]["locator_init_params"])
    cloud_init_params = current_settings["sys"]["cloud_init_params"]
    if current_settings["sys"]["cloud"] & default_values_sys._cloud.quecIot:
        cloud = QuecThing(
            cloud_init_params["PK"],
            cloud_init_params["PS"],
            cloud_init_params["DK"],
            cloud_init_params["DS"],
            cloud_init_params["SERVER"],
            mcu_name=PROJECT_NAME,
            mcu_version=PROJECT_VERSION
        )
        cloud_om = QuecObjectModel()
        cloud_object_model = quec_object_model
    elif current_settings["sys"]["cloud"] & default_values_sys._cloud.AliYun:
        cloud = AliYunIot(
            cloud_init_params["PK"],
            cloud_init_params["PS"],
            cloud_init_params["DK"],
            cloud_init_params["DS"],
            cloud_init_params["SERVER"],
            burning_method=1,
            mcu_name=PROJECT_NAME,
            mcu_version=PROJECT_VERSION,
            firmware_name=DEVICE_FIRMWARE_NAME,
            firmware_version=DEVICE_FIRMWARE_VERSION
        )
        cloud_om = AliObjectModel()
        cloud_object_model = ali_object_model
    else:
        raise TypeError("Settings cloud[%s] is not support." % current_settings["sys"]["cloud"])

    history = History()
    remote_pub = RemotePublish()
    remote_sub = RemoteSubcribe()
    low_energy_rtc = LowEnergyRTC()
    # energy_led = LED()
    # running_led = LED()
    power_key = PowerKey() if PowerKey is not None else None
    usb = USB() if USB is not None else None
    data_call = dataCall
    ota_file_clear = OTAFileClear()

    collector.set_controller(controller)
    collector.set_devicecheck(devicecheck)
    collector.set_battery(battery)
    collector.set_sensor(sensor)
    collector.set_locator(locator)
    collector.set_cloud_om(cloud_om)
    collector.set_history(history)
    collector.init_cloud_object_module(cloud_object_model)

    remote_pub.set_cloud(cloud)
    remote_pub.addObserver(history)
    remote_sub.set_executor(collector)

    controller.set_remote_pub(remote_pub)
    controller.set_settings(settings)
    controller.set_low_energy_rtc(low_energy_rtc)
    # controller.set_energy_led(energy_led)
    # controller.set_running_led(running_led)
    controller.set_power_key(power_key, pwk_callback)
    controller.set_usb(usb, usb_callback)
    controller.set_data_call(data_call, None)
    controller.set_ota_file_clear(ota_file_clear)

    work_cycle_period = current_settings["app"]["work_cycle_period"]
    low_energy_rtc.set_period(work_cycle_period)
    low_energy_rtc.set_low_energy_method(collector.__get_low_energy_method(work_cycle_period))
    low_energy_rtc.addObserver(collector)

    devicecheck.set_locator(locator)

    # TODO: Get tempreture from sensor.
    battery.set_temp(20)

    cloud.addObserver(remote_sub)
    cloud.set_object_model(collector.cloud_om)
    cloud.init()

    controller.ota_file_clean()
    collector.device_status_check()
    controller.low_energy_rtc_init()
    controller.low_energy_rtc_start()
