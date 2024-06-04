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
@file      :tracker.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :<description>
@version   :1.0.0
@date      :2023-01-04 15:15:36
@copyright :Copyright (c) 2022
"""
import pm
import utime
import _thread
from machine import UART, RTC
from usr.logging import getLogger
from usr.net_manage import NetManage
from usr.thingsboard import TBDeviceTCPClient
from usr.location import GPS, NMEAParse, CoordinateSystemConvert

log = getLogger(__name__)

gps_cfg = {
    "UARTn": UART.UART2,
    "buadrate": 115200,
    "databits": 8,
    "parity": 0,
    "stopbits": 1,
    "flowctl": 0,
    "gps_mode": 0x2,
    "nmea": 0b010111,
    "PowerPin": None,
    "StandbyPin": None,
    "BackupPin": None,
}

cloud_tcp_cfg = {
    "host": "106.15.58.32",
    "port": 5000,
    "timeout": 30
}


class Tracker:

    def __init__(self):
        self.__gps = None
        self.__nmea_parse = None
        self.__net_manage = None
        self.__cloud = None
        self.__csc = None

    def __rtc_callback(self, args):
        _thread.stack_size(0x2000)
        _thread.start_new_thread(self.running, ())

    def add_modules(self, module):
        if isinstance(module, NetManage):
            self.__net_manage = module
        elif isinstance(module, GPS):
            self.__gps = module
        elif isinstance(module, NMEAParse):
            self.__nmea_parse = module
        elif isinstance(module, TBDeviceTCPClient):
            self.__cloud = module
        elif isinstance(module, CoordinateSystemConvert):
            self.__csc = module

    def running(self):
        log.debug("Tracker running start.")
        # Get pm lock for device not into autosleep.
        pm_lock = pm.create_wakelock("pm_lock", 7)
        pm.wakelock_lock(pm_lock)

        # Check net connect.
        if not self.__net_manage.status:
            if self.__net_manage.wait_connect() == (3, 1):
                self.__net_manage.sync_time()

        # Get GPS data.
        gps_res = self.__gps.read(retry=10)
        Longitude, Latitude, Speed = [None] * 3
        if gps_res[0] == 0:
            self.__nmea_parse.set_gps_data(gps_res[1])
            Longitude = self.__nmea_parse.Longitude
            Latitude = self.__nmea_parse.Latitude
            Speed = self.__nmea_parse.Speed
        if Longitude and Latitude:
            Longitude, Latitude = self.__csc.wgs84_to_gcj02(Longitude, Latitude)
        loc_data = {
            "longitude": Longitude if Longitude is not None else -1,
            "latitude": Latitude if Latitude is not None else -1,
            "Speed": Speed if Speed is not None else -1
        }

        # Cloud connect and report location data to cloud.
        if self.__net_manage.status:
            if not self.__cloud.status:
                self.__cloud.disconnect()
                utime.sleep(6)
                self.__cloud.connect()
            log.debug("self.__cloud.status: %s" % self.__cloud.status)
            if self.__cloud.status:
                loc_data.update({
                    "sensorType": "GNSS",
                    "sensorModel": "LC86L"
                })
                res = self.__cloud.send_telemetry(loc_data)
                log.debug("Loc data report %s" % res)
            # self.__cloud.disconnect()

        # Start RTC wakeup after 60s.
        _timer = RTC()
        atime = utime.localtime(utime.mktime(utime.localtime()) + 20)
        alarm_time = [atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0]
        log.debug("alarm_time: %s" % str(alarm_time))
        _timer.register_callback(self.__rtc_callback)
        _res = _timer.set_alarm(tuple(alarm_time))
        log.debug("set_alarm res %s." % _res)
        if _res == 0:
            _timer.enable_alarm(1)

        # Release pm lock for device into autosleep.
        pm.autosleep(1)
        pm.wakelock_unlock(pm_lock)
        pm.delete_wakelock(pm_lock)
        log.debug("Tracker running over.")


def main():
    # Initialize modules.
    gps = GPS(**gps_cfg)
    nmea_parse = NMEAParse()
    net_manage = NetManage("QuecPython-Tracker", "v2.2.1")
    cloud = TBDeviceTCPClient(**cloud_tcp_cfg)
    csc = CoordinateSystemConvert()
    tracker = Tracker()

    # Add device modules to tracker module.
    tracker.add_modules(gps)
    tracker.add_modules(nmea_parse)
    tracker.add_modules(net_manage)
    tracker.add_modules(cloud)
    tracker.add_modules(csc)

    # Tracker running.
    tracker.running()


if __name__ == "__main__":
    main()
