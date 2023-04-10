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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@file      :tracker_tb.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :<description>
@version   :1.0.0
@date      :2022-10-31 11:15:57
@copyright :Copyright (c) 2022
"""
import gc
import sim
import utime
import modem
import _thread
# from machine import I2C
from misc import Power
from usr.modules.battery import Battery
from usr.modules.history import History
from usr.modules.logging import getLogger
from usr.modules.net_manage import NetManage
from usr.modules.mpower import LowEnergyManage
# from usr.modules.temp_humidity_sensor import TempHumiditySensor
from usr.modules.thingsboard import TBDeviceMQTTClient
from usr.modules.location import CoordinateSystemConvert, NMEAParse, GPS, CellLocator, WiFiLocator
from usr.settings_user import UserConfig
from usr.settings import Settings, PROJECT_NAME, PROJECT_VERSION, DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION, LOWENERGYMAP

log = getLogger(__name__)


class Tracker:

    def __init__(self):
        self.__settings = None
        self.__cell = None
        self.__wifi = None
        self.__gps = None
        self.__nmea_parse = None
        self.__battery = None
        self.__history = None
        self.__net_manage = None
        self.__tb_ota = None
        self.__tb_cloud = None
        self.__tb_objmodel = None
        self.__low_energy_manage = None
        self.__temp_humidity_sensor = None
        self.__wakeup = True
        self.__coor_sys_convert = None

    def __format_loc_method(self, data):
        loc_method = "%04d" % int(bin(data)[2:])
        _loc_method = {
            "gps": bool(int(loc_method[-1])),
            "cell": bool(int(loc_method[-2])),
            "wifi": bool(int(loc_method[-3])),
        }
        return _loc_method

    def __get_local_time(self):
        return str(utime.mktime(utime.localtime()) * 1000)

    def __get_location(self):
        res = {}
        loc_method = self.__settings.get()["user_cfg"]["loc_method"]
        map_coordinate_system = self.__settings.get()["loc_cfg"]["map_coordinate_system"]
        Longitude, Latitude, Speed = [None] * 3
        if loc_method & UserConfig._loc_method.gps:
            gps_res = self.__gps.read(retry=300)
            if gps_res[0] == 0:
                self.__nmea_parse.set_gps_data(gps_res[1])
                Longitude = self.__nmea_parse.Longitude
                Latitude = self.__nmea_parse.Latitude
                Speed = self.__nmea_parse.Speed
        if Longitude and Latitude:
            if map_coordinate_system == "GCJ02":
                Longitude, Latitude = self.__coor_sys_convert.wgs84_to_gcj02(Longitude, Latitude)
        res = {
            "longitude": Longitude,
            "latitude": Latitude,
            "speed": Speed
        }
        return res

    def __init_report_data(self, power_switch=True):
        _data = {}
        # _settings = self.__settings.get()

        # _data.update({
        #     "power_switch": power_switch,
        #     "local_time": self.__get_local_time(),
        #     "gps_mode": _settings["loc_cfg"]["gps_cfg"]["gps_mode"]
        # })

        # _data.update(_settings["user_cfg"])
        # _data.update({"loc_method": self.__format_loc_method(_settings["user_cfg"]["loc_method"])})

        _data.update(self.__get_location())

        # temperature, humidity = self.__temp_humidity_sensor.read() if self.__temp_humidity_sensor else (None, None)
        # _data.update({
        #     "temperature": temperature if temperature is not None else "",
        #     "humidity": humidity if humidity is not None else "",
        # })

        # self.__battery.set_temp(temperature if temperature is not None else 20)
        # _data.update({
        #     "energy": self.__battery.energy,
        #     "voltage": self.__battery.voltage,
        # })

        # _data.update(self.__init_alarm_data(_data))
        # log.debug("report_data: %s" % _data)

        return _data

    def __init_alarm_data(self, data):
        alarm_data = {}
        _settings = self.__settings.get()
        if _settings["user_cfg"]["sw_low_power_alert"]:
            if data["energy"] <= _settings["user_cfg"]["low_power_alert_threshold"]:
                alarm_data["low_power_alert"] = {"local_time": self.__get_local_time()}

        # if data["energy"] <= _settings["user_cfg"]["low_power_shutdown_threshold"]:
        #     alarm_data["power_switch"] = False
        #     self.__wakeup = False

        if _settings["user_cfg"]["sw_over_speed_alert"] and data.get("gps"):
            vtg_data = self.__nmea_parse.GxVTGData
            alarm_data["current_speed"] = float(vtg_data[7]) if vtg_data else -1.0
            if alarm_data["current_speed"] >= _settings["user_cfg"]["over_speed_threshold"]:
                alarm_data["over_speed_alert"] = {"local_time": self.__get_local_time()}

        net_status = self.__net_manage.status
        alarm_data["device_module_status"] = {}
        alarm_data["device_module_status"]["net"] = 1 if net_status else 0
        if self.__gps or self.__cell or self.__wifi:
            alarm_data["device_module_status"]["location"] = 1 if data.get("gps") or data.get("cell") or data.get("wifi") else 0
        if self.__temp_humidity_sensor:
            alarm_data["device_module_status"]["temp_sensor"] = 1 if data.get("temperature") is not None and data.get("humidity") is not None else 0

        # TODO: Add light-Sensor, G-Senor, Mike modules.

        if 0 in alarm_data["device_module_status"].values():
            alarm_data["fault_alert"] = {"local_time": self.__get_local_time()}
        if sim.getStatus() != 1:
            alarm_data["sim_abnormal_alert"] = {"local_time": self.__get_local_time()}

        return alarm_data

    def __data_report(self, data):
        res = False
        if self.__cloud_conn_status():
            log.debug("send_telemetry data: %s" % str(data))
            res = self.__tb_cloud.send_telemetry(data)
        log.debug("Ali object model report %s." % ("success" if res else "falied"))
        if not res:
            self.__history.write([data])
        return res

    def __history_report(self):
        if self.__history and self.__tb_cloud and self.__tb_objmodel:
            history_data = self.__history.read()["data"]
            if history_data:
                for index, _data in enumerate(history_data):
                    if not self.__data_report(data=_data):
                        break
                self.__history.write(history_data[index + 1:])

    def __set_config(self, data):
        _settings = self.__settings.get()
        for k, v in data.items():
            mode = ""
            if k in _settings["user_cfg"].keys():
                mode = "user_cfg"
                if k == "user_ota_action":
                    if _settings["user_cfg"]["sw_ota"] and not _settings["user_cfg"]["sw_ota_auto_upgrade"]:
                        if not (_settings["user_cfg"]["ota_status"]["upgrade_status"] == 1 and
                                _settings["user_cfg"]["user_ota_action"] == -1):
                            continue
                if k == "loc_method":
                    v = (int(v.get("wifi", 0)) << 2) + (int(v.get("cell", 0)) << 1) + int(v.get("gps", 0))
                res = self.__settings.set(mode, k, v)
                if k == "user_ota_action":
                    self.__tb_cloud.ota_search()
            elif k in _settings["cloud_cfg"].keys():
                mode = "cloud_cfg"
                res = self.__settings.set(mode, k, v)
            else:
                log.warn("Key %s is not find in settings. Value: %s" % (k, v))

            if mode:
                log.debug("Settings set %s %s to %s %s" % (mode, k, v, "success" if res else "falied"))
        self.__settings.save()

    def __set_objmodel(self, data):
        data = self.__tb_objmodel.convert_to_client(data)
        log.debug("set_objmodel data: %s" % str(data))
        self.__set_config(data)
        if "power_switch" in data.keys():
            _data = self.__init_report_data(power_switch=bool(data["power_switch"]))
            self.__data_report(_data)
            if bool(data["power_switch"]) is False:
                Power.powerDown()
        if "power_restart" in data.keys():
            _data = self.__init_report_data(power_switch=False)
            self.__data_report(_data)
            Power.powerRestart()
        if "work_cycle_period" in data.keys():
            self.__low_energy_manage.stop()
            self.__low_energy_manage.set_period(data["work_cycle_period"])
            method = self.init_low_energy_method(data["work_cycle_period"])
            self.__low_energy_manage.set_method(method)
            self.__low_energy_manage.set_callback(self.running)
            self.__low_energy_manage.start()

    def __query_objmodel(self, data):
        objmodel_codes = [self.__tb_objmodel.id_code.get(i) for i in data if self.__tb_objmodel.id_code.get(i)]
        log.debug("query_objmodel ids: %s, codes: %s" % (str(data, str(objmodel_codes))))
        report_data = self.__init_report_data()
        self.__data_report(report_data)

    def __set_ota_status(self, target_module, target_version, status):
        ota_status = self.__settings.get()["user_cfg"]["ota_status"]
        ota_info = {}
        pass_flag = False
        if ota_status["sys_target_version"] == "--" and ota_status["app_target_version"] == "--":
            if target_module == DEVICE_FIRMWARE_NAME:
                if target_version != DEVICE_FIRMWARE_VERSION:
                    ota_info["upgrade_module"] = 1
                    ota_info["sys_target_version"] = target_version
                else:
                    pass_flag = True
            elif target_module == PROJECT_NAME:
                if target_version != PROJECT_VERSION:
                    ota_info["upgrade_module"] = 2
                    ota_info["app_target_version"] = target_version
                else:
                    pass_flag = True
        if pass_flag is False:
            ota_info["upgrade_status"] = status
        ota_status.update(ota_info)
        self.__set_config({"ota_status": ota_status})

    def __ota_plain_check(self, target_module, target_version, battery_limit, min_signal_intensity, use_space):
        _settings = self.__settings.get()
        if _settings["user_cfg"]["sw_ota"]:
            self.__set_ota_status(target_module, target_version, 1)
            if _settings["user_cfg"]["sw_ota_auto_upgrade"] or _settings["user_cfg"]["user_ota_action"] != -1:
                if _settings["user_cfg"]["sw_ota_auto_upgrade"]:
                    _ota_action = 1
                else:
                    if _settings["user_cfg"]["user_ota_action"] != -1:
                        _ota_action = _settings["user_cfg"]["user_ota_action"]
                    else:
                        return
            upgrade_module = 1 if target_module == DEVICE_FIRMWARE_NAME else 2
            source_version = DEVICE_FIRMWARE_VERSION if target_module == DEVICE_FIRMWARE_NAME else PROJECT_VERSION
            if _settings['user_cfg']['ota_status']['upgrade_module'] == upgrade_module and \
                    _settings['user_cfg']['ota_status']['upgrade_status'] <= 1 and \
                    target_version != source_version:
                if _ota_action == 1:
                    # TODO: Check battery_limit, min_signal_intensity, use_space
                    pass
                self.__tb_cloud.ota_action(action=_ota_action)
        else:
            self.__tb_cloud.ota_action(action=0)

    def __ota(self, errcode, data):
        if errcode == 10700 and data:
            data = eval(data)
            target_module = data[0]
            # source_version = data[1]
            target_version = data[2]
            battery_limit = data[3]
            min_signal_intensity = data[4]
            use_space = data[5]
            self.__ota_plain_check(target_module, target_version, battery_limit, min_signal_intensity, use_space)
        elif errcode == 10701:
            data = eval(data)
            target_module = data[0]
            length = data[1]
            md5 = data[2]
            self.__set_ota_status(None, None, 2)
            self.__tb_ota.set_ota_info(length, md5)
        elif errcode == 10702:
            self.__set_ota_status(None, None, 2)
        elif errcode == 10703:
            data = eval(data)
            target_module = data[0]
            length = data[1]
            start_addr = data[2]
            piece_length = data[3]
            self.__set_ota_status(None, None, 2)
            self.__tb_ota.start_ota(start_addr, piece_length)
        elif errcode == 10704:
            self.__set_ota_status(None, None, 3)
        elif errcode == 10705:
            self.__set_ota_status(None, None, 4)
        elif errcode == 10706:
            self.__set_ota_status(None, None, 4)

    def __cloud_conn_status(self):
        if not self.__tb_cloud.status:
            self.__net_manage.reconnect()
        if not self.__tb_cloud.status:
            disconn_res = self.__tb_cloud.disconnect()
            conn_res = self.__tb_cloud.connect()
            log.debug("Quec cloud reconnect. disconnect: %s connect: %s" % (disconn_res, conn_res))
        return self.__tb_cloud.status

    def __init_ota_status(self):
        _settings = self.__settings.get()
        ota_status = _settings["user_cfg"]["ota_status"]
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
            self.__set_config({"ota_status": ota_status})

    def add_module(self, module):
        if isinstance(module, Settings):
            self.__settings = module
            return True
        elif isinstance(module, Battery):
            self.__battery = module
            return True
        elif isinstance(module, GPS):
            self.__gps = module
            return True
        elif isinstance(module, History):
            self.__history = module
            return True
        elif isinstance(module, NetManage):
            self.__net_manage = module
            return True
        # elif isinstance(module, TempHumiditySensor):
        #     self.__temp_humidity_sensor = module
        #     return True
        elif isinstance(module, LowEnergyManage):
            self.__low_energy_manage = module
            return True
        elif isinstance(module, TBDeviceMQTTClient):
            self.__tb_cloud = module
            return True
        elif isinstance(module, NMEAParse):
            self.__nmea_parse = module
            return True
        elif isinstance(module, CellLocator):
            self.__cell = module
            return True
        elif isinstance(module, WiFiLocator):
            self.__wifi = module
            return True
        elif isinstance(module, CoordinateSystemConvert):
            self.__coor_sys_convert = module
            return True
        return False

    def running(self, args):
        log.debug("[tracker][running][start] gc.mem_alloc(): %skb" % (gc.mem_alloc() / 1024))
        # Init device ota infomation.
        self.__init_ota_status()
        # Check device net.
        if not self.__net_manage.status:
            if self.__net_manage.wait_connect != (3, 1):
                self.__net_manage.reconnect()
        _settings = self.__settings.get()
        # # QuecIot connect and save device secret.
        # if _settings["cloud_cfg"]["dk"] and not _settings["cloud_cfg"]["ds"] and self.__tb_cloud.device_secret:
        #     self.__set_config({"ds": self.__tb_cloud.device_secret})
        # Histort report
        self.__history_report()
        # Data report
        power_switch = True if args != "POWERDOWN" else False
        report_data = self.__init_report_data(power_switch=power_switch)
        self.__data_report(report_data)
        # OTA status reset
        if _settings["user_cfg"]["ota_status"]["upgrade_status"] in (3, 4):
            cfg_data = {
                "ota_status": {
                    "sys_current_version": DEVICE_FIRMWARE_VERSION,
                    "sys_target_version": "--",
                    "app_current_version": PROJECT_VERSION,
                    "app_target_version": "--",
                    "upgrade_module": 0,
                    "upgrade_status": 0,
                }
            }
            if _settings["user_cfg"]["user_ota_action"] != -1:
                cfg_data["user_ota_action"] = -1
            self.__set_config(cfg_data)
        # Device version report and OTA plain search
        # if self.__cloud_conn_status():
        #     _res = self.__tb_cloud.device_report()
        #     log.debug("Quec device report %s" % "success" if _res else "falied")
        #     _res = self.__tb_cloud.ota_request()
        #     log.debug("Quec ota request %s" % "success" if _res else "falied")
        # Device need to powerdown and not to wakeup
        if self.__wakeup:
            _res = self.__low_energy_manage.start()
            log.debug("Module start low enenery manage %s." % ("success" if _res else "falied"))
        else:
            _res = self.__low_energy_manage.stop()
            log.debug("Module stop low enenery manage %s." % ("success" if _res else "falied"))
        # Device powerdown
        # if report_data["power_switch"] is False:
        #     Power.powerDown()
        log.debug("[tracker][running][end] gc.mem_alloc(): %skb" % (gc.mem_alloc() / 1024))
        gc.collect()
        log.debug("[tracker][running][collect over] gc.mem_alloc(): %skb" % (gc.mem_alloc() / 1024))

    def execute(self, args):
        if args[0] == 5 and args[1] == 10200:
            log.debug("transparent data: %s" % args[1])
        elif args[0] == 5 and args[1] == 10210:
            self.__set_objmodel(args[2])
        elif args[0] == 5 and args[1] == 10220:
            self.__query_objmodel(args[2])
        elif args[0] == 7:
            log.debug("QuecIot OTA errcode[%s] data[%s]" % tuple(args[1:]))
            self.__ota(*args[1:])
        else:
            log.error("Mode %s is not support. data: %s" % (str(args[0]), str(args[1])))

    def init_low_energy_method(self, period):
        device_model = modem.getDevModel()
        support_methods = [_method for _method in LOWENERGYMAP.keys() if device_model in LOWENERGYMAP[_method]]
        method = "NULL"
        if support_methods:
            if period >= self.__settings.get()["user_cfg"]["work_mode_timeline"]:
                if "PSM" in support_methods:
                    method = "PSM"
                elif "POWERDOWN" in support_methods:
                    method = "POWERDOWN"
                elif "PM" in support_methods:
                    method = "PM"
            else:
                if "PM" in support_methods:
                    method = "PM"
        log.debug("init_low_energy_method: %s" % method)
        return method


def main():
    log.debug("[main] [start] gc.mem_alloc(): %skb" % (gc.mem_alloc() / 1024))
    _thread.stack_size(1024 * 8)
    log.info("PROJECT_NAME: %s, PROJECT_VERSION: %s" % (PROJECT_NAME, PROJECT_VERSION))
    log.info("DEVICE_FIRMWARE_NAME: %s, DEVICE_FIRMWARE_VERSION: %s" % (DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION))

    # 初始化配置参数模块
    settings = Settings()
    _settings = settings.get()
    log.debug("_settings: %s" % str(_settings))
    # 初始化电池模块
    battery = Battery()
    # 初始化历史信息模块
    history = History()
    # 初始化网络管理模块
    net_manage = NetManage(PROJECT_NAME, PROJECT_VERSION)
    # 初始化温湿度传感器模块
    # temp_humidity_sensor = TempHumiditySensor(I2C.I2C1, I2C.STANDARD_MODE)
    # 初始化低功耗管理模块
    low_energy_manage = LowEnergyManage()

    # 初始化GPS原始数据解析模块
    nema_parse = NMEAParse()
    # 初始化GPS模块
    gps = GPS(**_settings["loc_cfg"]["gps_cfg"])
    coor_sys_convert = CoordinateSystemConvert()

    # 初始化移远云与OTA模块
    tb_cloud = TBDeviceMQTTClient(**_settings["cloud_cfg"])

    # Tracker 实例化对象
    tracker = Tracker()
    # 注册功能模块
    tracker.add_module(settings)
    tracker.add_module(battery)
    tracker.add_module(history)
    tracker.add_module(net_manage)
    # tracker.add_module(temp_humidity_sensor)
    tracker.add_module(low_energy_manage)
    tracker.add_module(tb_cloud)
    tracker.add_module(nema_parse)
    tracker.add_module(gps)
    tracker.add_module(coor_sys_convert)

    # 云端设置下行消息回调函数
    tb_cloud.set_callback(tracker.execute)
    res = tb_cloud.connect()
    log.debug("TB cloud connect %s" % res)

    # 低功耗设置唤醒回调函数
    low_energy_manage.set_callback(tracker.running)
    low_energy_manage.set_period(_settings["user_cfg"]["work_cycle_period"])
    # low_energy_manage.set_method(tracker.init_low_energy_method(_settings["user_cfg"]["work_cycle_period"]))
    low_energy_manage.set_method("NULL")

    # 启动Tracker业务功能(循环设备状态检测与信息上报, 进入低功耗模式)
    tracker.running(None)
    log.debug("[main] [end] gc.mem_alloc(): %skb" % (gc.mem_alloc() / 1024))


if __name__ == "__main__":
    main()
