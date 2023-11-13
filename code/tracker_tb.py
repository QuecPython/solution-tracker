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
@file      :tracker_tb.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :Tracker by ThingsBoard.
@version   :2.2.0
@date      :2023-04-14 14:30:13
@copyright :Copyright (c) 2022
"""

import utime
import _thread
import usys as sys
from misc import Power
from queue import Queue
from machine import RTC, I2C

from usr.settings_user import UserConfig
from usr.settings import Settings, PROJECT_NAME, PROJECT_VERSION
from usr.modules.battery import Battery
from usr.modules.history import History
from usr.modules.logging import getLogger
from usr.modules.net_manage import NetManage
from usr.modules.thingsboard import TBDeviceMQTTClient
from usr.modules.power_manage import PowerManage, PMLock
from usr.modules.temp_humidity_sensor import TempHumiditySensor
from usr.modules.location import GNSS, CellLocator, WiFiLocator, NMEAParse, CoordinateSystemConvert

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
        self.__nmea_parse = None
        self.__csc = None
        self.__net_manage = None
        self.__pm = None
        self.__temp_sensor = None
        self.__settings = None

        self.__business_lock = PMLock("block")
        self.__business_tid = None
        self.__business_rtc = RTC()
        self.__business_queue = Queue()
        self.__business_tag = 0
        self.__running_tag = 0
        self.__server_ota_flag = 0

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
                    elif data[1] == "into_sleep":
                        _thread.stack_size(0x1000)
                        _thread.start_new_thread(self.__into_sleep, ())
                if data[0] == 1:
                    self.__server_option(*data[1])
                self.__business_tag = 0

    def __loc_report(self):
        properties = self.__get_device_infos()
        if self.__net_connect():
            self.__history_report()
            res = self.__server.send_telemetry(properties)
            if not res:
                self.__history.write([properties])

    def __history_report(self):
        failed_datas = []
        his_datas = self.__history.read()
        if his_datas["data"]:
            for item in his_datas["data"]:
                res = self.__server.send_telemetry(item)
                if not res:
                    failed_datas.append(item)
        if failed_datas:
            self.__history.write(failed_datas)

    def __get_device_infos(self):
        properties = self.__get_loc_data()
        return properties

    def __get_loc_data(self):
        loc_state = 0
        loc_data = {
            "Longitude": 181,
            "Latitude": 91,
            "Altitude": -1,
            "Speed": -1,
        }
        loc_cfg = self.__settings.read("loc")
        user_cfg = self.__settings.read("user")
        if user_cfg["loc_method"] & UserConfig._loc_method.gps:
            res = self.__gnss.read(user_cfg["loc_gps_read_timeout"])
            if res[0] == 0:
                gnss_data = res[1]
                self.__nmea_parse.set_gps_data(gnss_data)
                loc_data["Longitude"] = float(self.__nmea_parse.Longitude)
                loc_data["Latitude"] = float(self.__nmea_parse.Latitude)
                loc_data["Altitude"] = float(self.__nmea_parse.Altitude)
                loc_data["current_speed"] = float(self.__nmea_parse.Speed)
                loc_state = 1
        if loc_state == 0 and user_cfg["loc_method"] & UserConfig._loc_method.cell:
            res = self.__cell.read()
            if res:
                loc_data["Longitude"] = res[0]
                loc_data["Latitude"] = res[1]
                loc_state = 1
        if loc_state == 0 and user_cfg["loc_method"] & UserConfig._loc_method.wifi:
            res = self.__wifi.read()
            if res:
                loc_data["Longitude"] = res[0]
                loc_data["Latitude"] = res[1]
                loc_state = 1
        if loc_state == 1 and loc_cfg["map_coordinate_system"] == "GCJ02":
            lng, lat = self.__csc.wgs84_to_gcj02(loc_data["Longitude"], loc_data["Latitude"])
            loc_data["Longitude"] = lng
            loc_data["Latitude"] = lat
        return loc_data

    def __net_connect(self, retry=2):
        res = False
        if not self.__net_manage.status:
            log.debug("Net not connect, try to reconnect.")
            self.__net_manage.reconnect()
            self.__net_manage.wait_connect()

        if self.__net_manage.sim_status == 1:
            count = 0
            while not self.__net_manage.status:
                log.debug("Net reconnect times %s" % count)
                self.__net_manage.reconnect()
                self.__net_manage.wait_connect()
                if self.__net_manage.status or count >= retry:
                    break
                count += 1
            if self.__net_manage.status:
                self.__net_manage.sync_time()
                count = 0
                while True:
                    if self.__server.status:
                        break
                    self.__server.disconnect()
                    if self.__server.connect() or count >= retry:
                        break
                    count += 1
                    utime.sleep_ms(100)
            res = self.__server.status
        else:
            log.debug("Sim card is not ready.")
        return res

    def __into_sleep(self):
        while True:
            if self.__business_queue.size() == 0 and self.__business_tag == 0:
                break
            utime.sleep_ms(500)
        user_cfg = self.__settings.read("user")
        if user_cfg["work_cycle_period"] < user_cfg["work_mode_timeline"]:
            self.__pm.autosleep(1)
        else:
            self.__pm.set_psm(mode=1, tau=user_cfg["work_cycle_period"], act=5)
        self.__set_rtc(user_cfg["work_cycle_period"], self.running)

    def __set_rtc(self, period, callback):
        self.__business_rtc.enable_alarm(0)
        if callback and callable(callback):
            self.__business_rtc.register_callback(callback)
        atime = utime.localtime(utime.mktime(utime.localtime()) + period)
        alarm_time = (atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0)
        _res = self.__business_rtc.set_alarm(alarm_time)
        log.debug("alarm_time: %s, set_alarm res %s." % (str(alarm_time), _res))
        return self.__business_rtc.enable_alarm(1) if _res == 0 else -1

    def __server_option(self, topic, data):
        # TODO:
        pass

    def __power_restart(self):
        log.debug("__power_restart")
        Power.powerRestart()

    def add_module(self, module):
        if isinstance(module, TBDeviceMQTTClient):
            self.__server = module
        elif isinstance(module, Battery):
            self.__battery = module
        elif isinstance(module, History):
            self.__history = module
        elif isinstance(module, GNSS):
            self.__gnss = module
        elif isinstance(module, CellLocator):
            self.__cell = module
        elif isinstance(module, WiFiLocator):
            self.__wifi = module
        elif isinstance(module, NMEAParse):
            self.__nmea_parse = module
        elif isinstance(module, CoordinateSystemConvert):
            self.__csc = module
        elif isinstance(module, NetManage):
            self.__net_manage = module
        elif isinstance(module, PowerManage):
            self.__pm = module
        elif isinstance(module, TempHumiditySensor):
            self.__temp_sensor = module
        elif isinstance(module, Settings):
            self.__settings = module
        else:
            return False
        return True

    def running(self, args=None):
        if self.__running_tag == 1:
            return
        self.__running_tag = 1

        # Disable sleep.
        self.__pm.autosleep(0)
        self.__pm.set_psm(mode=0)

        self.__business_start()
        self.__business_queue.put((0, "loc_report"))
        self.__business_queue.put((0, "into_sleep"))
        self.__running_tag = 0

    def server_callback(self, args):
        self.__business_queue.put((1, args))

    def net_callback(self, args):
        log.debug("net_callback args: %s" % str(args))
        if args[1] == 0:
            self.__server.disconnect()


def main():
    net_manage = NetManage(PROJECT_NAME, PROJECT_VERSION)
    settings = Settings()
    battery = Battery()
    history = History()
    server_cfg = settings.read("server")
    server = TBDeviceMQTTClient(**server_cfg)
    power_manage = PowerManage()
    temp_sensor = TempHumiditySensor(i2cn=I2C.I2C1, mode=I2C.FAST_MODE)
    loc_cfg = settings.read("loc")
    gnss = GNSS(**loc_cfg["gps_cfg"])
    cell = CellLocator(**loc_cfg["cell_cfg"])
    wifi = WiFiLocator(**loc_cfg["wifi_cfg"])
    nmea_parse = NMEAParse()
    cyc = CoordinateSystemConvert()

    tracker = Tracker()
    tracker.add_module(settings)
    tracker.add_module(battery)
    tracker.add_module(history)
    tracker.add_module(net_manage)
    tracker.add_module(server)
    tracker.add_module(power_manage)
    tracker.add_module(temp_sensor)
    tracker.add_module(gnss)
    tracker.add_module(cell)
    tracker.add_module(wifi)
    tracker.add_module(nmea_parse)
    tracker.add_module(cyc)

    net_manage.set_callback(tracker.net_callback)
    server.set_callback(tracker.server_callback)

    tracker.running()


if __name__ == "__main__":
    main()
