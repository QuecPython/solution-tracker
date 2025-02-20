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
import osTimer
from misc import Power
from queue import Queue
from machine import RTC

try:
    from settings import Settings
    from settings_user import UserConfig
    from modules.battery import Battery
    from modules.history import History
    from modules.logging import getLogger
    from modules.net_manage import NetManager
    from modules.thingsboard import TBDeviceMQTTClient
    from modules.power_manage import PowerManage, PMLock
    from modules.location import GNSS, GNSSBase, CellLocator, WiFiLocator, CoordinateSystemConvert
except ImportError:
    from usr.settings import Settings
    from usr.settings_user import UserConfig
    from usr.modules.battery import Battery
    from usr.modules.history import History
    from usr.modules.logging import getLogger
    from usr.modules.net_manage import NetManager
    from usr.modules.thingsboard import TBDeviceMQTTClient
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
        self.__settings = None

        self.__business_lock = PMLock("block")
        self.__business_tid = None
        self.__business_rtc = RTC()
        self.__business_queue = Queue()
        self.__business_tag = 0
        self.__server_ota_flag = 0
        self.__server_reconn_timer = osTimer()
        self.__server_conn_tag = 0
        self.__server_reconn_count = 0
        self.__reset_tag = 0

    def __business_start(self):
        if not self.__business_tid or (self.__business_tid and not _thread.threadIsRunning(self.__business_tid)):
            _thread.stack_size(0x2000)
            self.__business_tid = _thread.start_new_thread(self.__business_running, ())

    def __business_stop(self):
        self.__business_tid = None

    def __business_running(self):
        while self.__business_tid is not None or self.__business_queue.size() > 0:
            data = self.__business_queue.get()
            with self.__business_lock:
                self.__business_tag = 1
                if data[0] == 0:
                    if data[1] == "loc_report":
                        self.__loc_report()
                    if data[1] == "server_connect":
                        self.__server_connect()
                if data[0] == 1:
                    self.__server_option(data[1])
                self.__business_tag = 0

    def __loc_report(self):
        # Report current location.
        loc_state, properties = self.__get_loc_data()
        if loc_state == 1:
            res = False
            if self.__server.status:
                res = self.__server.send_telemetry(properties)
            if not res:
                self.__history.write([properties])

        # Report history location.
        if self.__server.status:
            self.__history_report()

        # Start report again timer.
        user_cfg = self.__settings.read("user")
        self.__set_rtc(user_cfg["work_cycle_period"], self.loc_report)

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

    def __get_loc_data(self):
        loc_state = 0
        loc_data = {
            "Longitude": 0.0,
            "Latitude": 0.0,
            "Altitude": 0.0,
            "Speed": 0.0,
        }
        loc_cfg = self.__settings.read("loc")
        user_cfg = self.__settings.read("user")
        if user_cfg["loc_method"] & UserConfig._loc_method.gps:
            res = self.__gnss.read()
            log.debug("gnss read %s" % str(res))
            if res["state"] == "A":
                loc_data["Latitude"] = float(res["lat"]) * (1 if res["lat_dir"] == "N" else -1)
                loc_data["Longitude"] = float(res["lng"]) * (1 if res["lng_dir"] == "E" else -1)
                loc_data["Altitude"] = res["altitude"]
                loc_data["Speed"] = res["speed"]
                loc_state = 1
        if loc_state == 0 and user_cfg["loc_method"] & UserConfig._loc_method.cell:
            res = self.__cell.read()
            if isinstance(res, tuple):
                loc_data["Longitude"] = res[0]
                loc_data["Latitude"] = res[1]
                loc_state = 1
        if loc_state == 0 and user_cfg["loc_method"] & UserConfig._loc_method.wifi:
            res = self.__wifi.read()
            if isinstance(res, tuple):
                loc_data["Longitude"] = res[0]
                loc_data["Latitude"] = res[1]
                loc_state = 1
        if loc_state == 1 and loc_cfg["map_coordinate_system"] == "GCJ02":
            lng, lat = self.__csc.wgs84_to_gcj02(loc_data["Longitude"], loc_data["Latitude"])
            loc_data["Longitude"] = lng
            loc_data["Latitude"] = lat
        return (loc_state, loc_data)

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
            self.__server.disconnect()
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

    def __server_option(self, args):
        topic, data = args
        log.debug("topic[%s]data[%s]" % args)
        # TODO: Handle server data.

    def __power_restart(self):
        if self.__reset_tag == 1:
            return
        self.__reset_tag = 1
        count = 0
        while (self.__business_queue.size() > 0 or self.__business_tag == 1) and count < 30:
            count += 1
            utime.sleep(1)
        log.debug("__power_restart")
        Power.powerRestart()

    def add_module(self, module):
        if isinstance(module, TBDeviceMQTTClient):
            self.__server = module
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

    def running(self):
        self.__business_start()
        self.server_connect(None)
        self.loc_report(None)

    def server_callback(self, topic, data):
        self.__business_queue.put((1, (topic, data)))

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


if __name__ == "__main__":
    # Init settings.
    settings = Settings()
    # Init battery.
    battery = Battery()
    # Init history
    history = History()
    # Init power manage and set device low energy.
    power_manage = PowerManage()
    power_manage.autosleep(1)
    # Init net modules and start net connect.
    net_manager = NetManager()
    _thread.stack_size(0x1000)
    _thread.start_new_thread(net_manager.net_connect, ())
    # Init GNSS modules and start reading and parsing gnss data.
    loc_cfg = settings.read("loc")
    gnss = GNSS(**loc_cfg["gps_cfg"])
    gnss.set_trans(0)
    gnss.start()
    # Init cell and wifi location modules.
    cell = CellLocator(**loc_cfg["cell_cfg"])
    wifi = WiFiLocator(**loc_cfg["wifi_cfg"])
    # Init coordinate system convert modules.
    cyc = CoordinateSystemConvert()
    # Init server modules.
    server_cfg = settings.read("server")
    server = TBDeviceMQTTClient(**server_cfg)
    # Init tracker business modules.
    tracker = Tracker()
    tracker.add_module(settings)
    tracker.add_module(battery)
    tracker.add_module(history)
    tracker.add_module(net_manager)
    tracker.add_module(server)
    tracker.add_module(gnss)
    tracker.add_module(cell)
    tracker.add_module(wifi)
    tracker.add_module(cyc)
    # Set net modules callback.
    net_manager.set_callback(tracker.net_callback)
    # Set server modules callback.
    server.set_callback(tracker.server_callback)
    # Start tracker business.
    tracker.running()
