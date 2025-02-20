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

"""
@file      :tracker_ali.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :Tracker by aliyun.
@version   :2.2.0
@date      :2023-04-11 11:43:11
@copyright :Copyright (c) 2022
"""

import sys
import utime
import _thread
import osTimer
from misc import Power
from queue import Queue
from machine import RTC

try:
    from settings_user import UserConfig
    from settings import Settings, PROJECT_NAME, PROJECT_VERSION, FIRMWARE_NAME, FIRMWARE_VERSION
    from modules.battery import Battery
    from modules.history import History
    from modules.logging import getLogger
    from modules.net_manage import NetManager
    from modules.aliIot import AliIot, AliIotOTA
    from modules.power_manage import PowerManage, PMLock
    from modules.location import GNSS, GNSSBase, CellLocator, WiFiLocator, CoordinateSystemConvert
except ImportError:
    from usr.settings_user import UserConfig
    from usr.settings import Settings, PROJECT_NAME, PROJECT_VERSION, FIRMWARE_NAME, FIRMWARE_VERSION
    from usr.modules.battery import Battery
    from usr.modules.history import History
    from usr.modules.logging import getLogger
    from usr.modules.net_manage import NetManager
    from usr.modules.aliIot import AliIot, AliIotOTA
    from usr.modules.power_manage import PowerManage, PMLock
    from usr.modules.location import GNSS, GNSSBase, CellLocator, WiFiLocator, CoordinateSystemConvert

log = getLogger(__name__)


class Tracker:

    def __init__(self):
        self.__server = None
        self.__server_ota = None
        self.__battery = None
        self.__history = None
        self.__gnss = None
        self.__cell = None
        self.__wifi = None
        self.__csc = None
        self.__net_manager = None
        self.__pm = None
        self.__settings = None

        self.__business_lock = PMLock("block")
        self.__business_tid = None
        self.__business_rtc = RTC()
        self.__business_queue = Queue()
        self.__business_tag = 0
        self.__running_tag = 0
        self.__server_ota_flag = 0
        self.__server_reconn_timer = osTimer()
        self.__server_conn_tag = 0
        self.__server_reconn_count = 0
        self.__reset_tag = 0

    def __business_start(self):
        if not self.__business_tid:
            _thread.stack_size(0x2000)
            self.__business_tid = _thread.start_new_thread(self.__business_running, ())

    def __business_stop(self):
        if self.__business_tid and _thread.threadIsRunning(self.__business_tid):
            try:
                _thread.stop_thread(self.__business_tid)
            except Exception as e:
                sys.print_exception(e)
        self.__business_tid = None

    def __business_running(self):
        while True:
            data = self.__business_queue.get()
            with self.__business_lock:
                self.__business_tag = 1
                if data[0] == 0:
                    if data[1] == "loc_report":
                        self.__loc_report()
                    elif data[1] == "server_connect":
                        self.__server_connect()
                    elif data[1] == "check_ota":
                        self.__server_check_ota()
                    elif data[1] == "ota_refresh":
                        self.__ota_cfg_refresh()
                if data[0] == 1:
                    self.__server_option(*data[1])
                self.__business_tag = 0

    def __loc_report(self):
        his_data = {"properties": {}, "events": []}
        loc_state, properties = self.__get_device_infos()
        alarms = self.__get_alarms(properties)
        res = False
        if self.__server.status:
            res = self.__server.properties_report(properties)
            if not res:
                his_data["properties"] = properties
            for alarm in alarms:
                res = self.__server.event_report(alarm, {})
                if not res:
                    his_data["events"].append(alarm)

        if loc_state and not self.__server.status:
            his_data["properties"] = properties
            his_data["events"] = alarms

        if his_data["properties"] or his_data["events"]:
            self.__history.write([his_data])

        self.__history_report()

        user_cfg = self.__settings.read("user")
        self.__set_rtc(user_cfg["work_cycle_period"], self.loc_report)

    def __history_report(self):
        failed_datas = []
        his_datas = self.__history.read()
        if his_datas["data"]:
            for item in his_datas["data"]:
                faile_data = {"properties": {}, "events": []}
                res = self.__server.properties_report(item["properties"])
                if not res:
                    faile_data["properties"] = item["properties"]
                for alarm in item["events"]:
                    res = self.__server.event_report(alarm, {})
                    if not res:
                        faile_data["events"].append(alarm)
                if faile_data["properties"] or faile_data["events"]:
                    failed_datas.append(faile_data)
        if failed_datas:
            self.__history.write(failed_datas)

    def __get_device_infos(self):
        user_cfg = self.__settings.read("user")
        loc_cfg = self.__settings.read("loc")
        properties = {
            "power_switch": 1,
            "energy": self.__battery.energy,
            "voltage": self.__battery.voltage,
            "local_time": str(utime.mktime(utime.localtime()) * 1000),
            "loc_method": {
                "gps": int((user_cfg["loc_method"] & UserConfig._loc_method.gps) / UserConfig._loc_method.gps),
                "cell": int((user_cfg["loc_method"] & UserConfig._loc_method.cell) / UserConfig._loc_method.cell),
                "wifi": int((user_cfg["loc_method"] & UserConfig._loc_method.wifi) / UserConfig._loc_method.wifi),
            },
            "phone_num": user_cfg["phone_num"],
            "work_mode": user_cfg["work_mode"],
            "work_cycle_period": user_cfg["work_cycle_period"],
            "low_power_alert_threshold": user_cfg["low_power_alert_threshold"],
            "low_power_shutdown_threshold": user_cfg["low_power_shutdown_threshold"],
            "sw_ota": user_cfg["sw_ota"],
            "sw_ota_auto_upgrade": user_cfg["sw_ota_auto_upgrade"],
            "sw_voice_listen": user_cfg["sw_voice_listen"],
            "sw_voice_record": user_cfg["sw_voice_record"],
            "sw_fault_alert": user_cfg["sw_fault_alert"],
            "sw_low_power_alert": user_cfg["sw_low_power_alert"],
            "sw_over_speed_alert": user_cfg["sw_over_speed_alert"],
            "sw_sim_abnormal_alert": user_cfg["sw_sim_abnormal_alert"],
            "sw_disassemble_alert": user_cfg["sw_disassemble_alert"],
            "sw_drive_behavior_alert": user_cfg["sw_drive_behavior_alert"],
            "drive_behavior_code": user_cfg["drive_behavior_code"],
            "over_speed_threshold": user_cfg["over_speed_threshold"],
            "user_ota_action": user_cfg["user_ota_action"],
            "ota_status": user_cfg["ota_status"],
            "work_mode_timeline": user_cfg["work_mode_timeline"],
            "loc_gps_read_timeout": user_cfg["loc_gps_read_timeout"],
            "gps_mode": loc_cfg["gps_cfg"]["gps_mode"],
            "device_module_status": {
                # "net": 0,
                # "location": 0,
                # "temp_sensor": 0,
                # "light_sensor": 0,
                # "move_sensor": 0,
                # "mike": 0,
            },
        }
        loc_state, loc_data = self.__get_loc_data()
        properties.update(loc_data)
        properties["device_module_status"]["location"] = 1 if properties["GeoLocation"]["Longitude"] else 0
        properties["device_module_status"]["temp_sensor"] = 1 if properties.get("temperature") is not None or properties.get("humidity") is not None else 0
        properties["device_module_status"]["net"] = int(self.__net_manager.net_status())
        return (loc_state, properties)

    def __get_loc_data(self):
        loc_state = 0
        loc_data = {
            "GeoLocation": {
                "Longitude": 0.0,
                "Latitude": 0.0,
                "Altitude": 0.0,
                "CoordinateSystem": 1,
            },
            "current_speed": 0,
        }
        loc_cfg = self.__settings.read("loc")
        loc_data["GeoLocation"]["CoordinateSystem"] = 1 if loc_cfg["map_coordinate_system"] == "WGS84" else 2
        user_cfg = self.__settings.read("user")
        if user_cfg["loc_method"] & UserConfig._loc_method.gps:
            res = self.__gnss.read()
            if res["state"] == "A":
                loc_data["GeoLocation"]["Latitude"] = float(res["lat"]) * (1 if res["lat_dir"] == "N" else -1)
                loc_data["GeoLocation"]["Longitude"] = float(res["lng"]) * (1 if res["lng_dir"] == "E" else -1)
                loc_data["GeoLocation"]["Altitude"] = res["altitude"]
                loc_data["current_speed"] = float(res["speed"])
                loc_state = 1
        if loc_state == 0 and user_cfg["loc_method"] & UserConfig._loc_method.cell:
            res = self.__cell.read()
            if res:
                loc_data["GeoLocation"]["Longitude"] = res[0]
                loc_data["GeoLocation"]["Latitude"] = res[1]
                loc_state = 1
        if loc_state == 0 and user_cfg["loc_method"] & UserConfig._loc_method.wifi:
            res = self.__wifi.read()
            if res:
                loc_data["GeoLocation"]["Longitude"] = res[0]
                loc_data["GeoLocation"]["Latitude"] = res[1]
                loc_state = 1
        if loc_state == 1 and loc_cfg["map_coordinate_system"] == "GCJ02":
            lng, lat = self.__csc.wgs84_to_gcj02(loc_data["GeoLocation"]["Longitude"], loc_data["GeoLocation"]["Latitude"])
            loc_data["GeoLocation"]["Longitude"] = lng
            loc_data["GeoLocation"]["Latitude"] = lat
        return (loc_state, loc_data)

    def __get_alarms(self, properties):
        alarms = []
        user_cfg = self.__settings.read("user")
        if user_cfg["sw_over_speed_alert"] and properties["current_speed"] >= user_cfg["over_speed_threshold"]:
            alarms.append("over_speed_alert")
        if user_cfg["sw_sim_abnormal_alert"] and self.__net_manager.sim_status() != 1:
            alarms.append("sim_abnormal_alert")
        if user_cfg["sw_low_power_alert"] and properties["energy"] < user_cfg["low_power_alert_threshold"]:
            alarms.append("low_power_alert")
        if user_cfg["sw_fault_alert"] and 0 in properties["device_module_status"].values():
            alarms.append("fault_alert")
        return alarms

    def __set_rtc(self, period, callback):
        self.__business_rtc.enable_alarm(0)
        if callback and callable(callback):
            self.__business_rtc.register_callback(callback)
        atime = utime.localtime(utime.mktime(utime.localtime()) + period)
        alarm_time = (atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0)
        _res = self.__business_rtc.set_alarm(alarm_time)
        log.debug("alarm_time: %s, set_alarm res %s." % (str(alarm_time), _res))
        return self.__business_rtc.enable_alarm(1) if _res == 0 else -1

    def __server_connect(self):
        if self.__net_manager.net_status():
            # self.__server.disconnect()
            self.__server.connect()
        if not self.__server.status:
            self.__server_reconn_timer.stop()
            self.__server_reconn_timer.start(60 * 1000, 0, self.server_connect)
            self.__server_reconn_count += 1
        else:
            self.__server_reconn_count = 0

        # When server not connect success after 20 miuntes, to reset device.
        if self.__server_reconn_count >= 20:
            _thread.stack_size(0x1000)
            _thread.start_new_thread(self.__power_restart, ())
        self.__server_conn_tag = 0

    def __server_cfg_save(self, data):
        save_tag = 0
        server_cfg = self.__settings.read("server")
        if server_cfg["product_key"] != data["product_key"]:
            server_cfg["product_key"] = data["product_key"]
            save_tag = 1
        if server_cfg["product_secret"] != data["product_secret"]:
            server_cfg["product_secret"] = data["product_secret"]
            save_tag = 1
        if server_cfg["device_name"] != data["device_name"]:
            server_cfg["device_name"] = data["device_name"]
            save_tag = 1
        if server_cfg["device_secret"] != data["device_secret"]:
            server_cfg["device_secret"] = data["device_secret"]
            save_tag = 1
        if save_tag == 1:
            self.__settings.save({"server": server_cfg})

    def __server_option(self, topic, data):
        if topic.endswith("/property/set"):
            self.__server_property_set(data)
        elif topic.find("/rrpc/request/") != -1:
            msg_id = topic.split("/")[-1]
            self.__server_rrpc_response(msg_id, data)
        elif topic.find("/thing/service/") != -1:
            service = topic.split("/")[-1]
            self.__server_service_response(service, data)
        elif topic.startswith("/ota/device/upgrade/") or topic.endswith("/ota/firmware/get_reply"):
            user_cfg = self.__settings.read("user")
            if self.__server_ota_flag == 0:
                if user_cfg["sw_ota"] == 1:
                    self.__server_ota_flag = 1
                    if user_cfg["sw_ota_auto_upgrade"] == 1 or user_cfg["user_ota_action"] == 1:
                        self.__server_ota_process(data)
                    else:
                        self.__server_ota_flag = 0
                        self.__server_ota.set_ota_data(data["data"])
                        ota_info = self.__server_ota.get_ota_info()
                        ota_info["ota_status"] = 1
                        self.__server_ota_state_save(**ota_info)
                else:
                    module = data.get("data", {}).get("module")
                    self.__server.ota_device_progress(-1, "Device is not alowed ota.", module)

    def __server_property_set(self, data):
        set_properties = data.get("params", {})
        user_cfg = self.__settings.read("user")
        user_cfg.update(set_properties)
        if self.__settings.save({"user": user_cfg}):
            self.__server.property_set_reply(data.get("id"), 200, "success")
            self.__business_queue.put((0, "loc_report"))
        else:
            self.__server.property_set_reply(data.get("id"), 9201, "save properties failed")

    def __server_ota_process(self, data):
        code = data.get("code")
        module = data.get("data", {}).get("module")
        if code in ("1000", 200) and module:
            self.__server.ota_device_progress(1, "", module)
            self.__server_ota.set_ota_data(data["data"])
            ota_info = self.__server_ota.get_ota_info()
            ota_info["ota_status"] = 2
            self.__server_ota_state_save(**ota_info)
            if self.__server_ota.start():
                ota_info["ota_status"] = 3
                self.__server_ota_state_save(**ota_info)
                self.__power_restart()
            else:
                ota_info["ota_status"] = 4
                self.__server_ota_state_save(**ota_info)
        self.__server_ota_flag = 0

    def __server_ota_state_save(self, ota_module, ota_version, ota_status):
        user_cfg = self.__settings.read("user")
        if ota_module == PROJECT_NAME:
            user_cfg["ota_status"]["upgrade_module"] = 2
            user_cfg["ota_status"]["upgrade_status"] = ota_status
            user_cfg["ota_status"]["app_target_version"] = ota_version
        if ota_module == FIRMWARE_NAME:
            user_cfg["ota_status"]["upgrade_module"] = 1
            user_cfg["ota_status"]["upgrade_status"] = ota_status
            user_cfg["ota_status"]["sys_target_version"] = ota_version
        self.__settings.save({"user": user_cfg})

    def __server_check_ota(self):
        if self.__server_ota_flag == 0 and self.__server.status:
            res = self.__server.ota_device_inform(PROJECT_VERSION, PROJECT_NAME)
            log.debug("ota_device_inform report project %s" % res)
            res = self.__server.ota_device_inform(FIRMWARE_VERSION, FIRMWARE_NAME)
            log.debug("ota_device_inform report firmware %s" % res)
            res = self.__server.ota_firmware_get(PROJECT_NAME)
            log.debug("ota_firmware_get project %s" % res)
            res = self.__server.ota_firmware_get(FIRMWARE_NAME)
            log.debug("ota_firmware_get firmware %s" % res)

    def __server_rrpc_response(self, msg_id, data):
        self.__server.rrpc_response(msg_id, data)

    def __server_service_response(self, service, data):
        msg_id = data.get("id")
        self.__server.service_response(service, 200, {}, msg_id, "success")

    def __power_restart(self):
        log.debug("__power_restart")
        Power.powerRestart()

    def __ota_cfg_refresh(self):
        user_cfg = self.__settings.read("user")
        if user_cfg["ota_status"]["upgrade_status"] in (3, 4):
            user_cfg["ota_status"]["upgrade_status"] = 0
            if user_cfg["ota_status"]["upgrade_module"] == 1:
                user_cfg["ota_status"]["sys_target_version"] = "--"
            if user_cfg["ota_status"]["upgrade_module"] == 2:
                user_cfg["ota_status"]["app_target_version"] = "--"
            user_cfg["ota_status"]["upgrade_module"] = 0
            user_cfg["user_ota_action"] = -1
        self.__settings.save({"user": user_cfg})

    def add_module(self, module):
        if isinstance(module, AliIot):
            self.__server = module
        elif isinstance(module, AliIotOTA):
            self.__server_ota = module
        elif isinstance(module, Battery):
            self.__battery = module
        elif isinstance(module, History):
            self.__history = module
        elif isinstance(module, GNSSBase):
            self.__gnss = module
        elif isinstance(module, CellLocator):
            self.__cell = module
        elif isinstance(module, WiFiLocator):
            self.__wifi = module
        elif isinstance(module, CoordinateSystemConvert):
            self.__csc = module
        elif isinstance(module, NetManager):
            self.__net_manager = module
        elif isinstance(module, Settings):
            self.__settings = module
        else:
            return False
        return True

    def running(self, args=None):
        self.__business_start()
        self.server_connect(None)
        self.__business_queue.put((0, "ota_refresh"))
        self.loc_report(None)
        self.__business_queue.put((0, "check_ota"))

    def server_callback(self, args):
        self.__business_queue.put((1, args))

    def net_callback(self, args):
        log.debug("net_callback args: %s" % str(args))
        if args[1] == 0:
            self.__server.disconnect()
            self.__server_reconn_timer.stop()
            self.__server_reconn_timer.start(30 * 1000, 0, self.server_connect)
        else:
            self.__server_reconn_timer.stop()
            self.server_connect(None)

    def loc_report(self, args):
        self.__business_queue.put((0, "loc_report"))

    def server_connect(self, args):
        if self.__server_conn_tag == 0:
            self.__server_conn_tag = 1
            self.__business_queue.put((0, "server_connect"))
