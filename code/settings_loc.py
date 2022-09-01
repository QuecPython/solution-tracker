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

from machine import UART


class LocConfig(object):

    class _gps_mode(object):
        none = 0x0
        internal = 0x1
        external = 0x2

    class _loc_method(object):
        none = 0x0
        gps = 0x1
        cell = 0x2
        wifi = 0x4
        all = 0x7

    class _map_coordinate_system(object):
        WGS84 = "WGS84"
        GCJ02 = "GCJ02"

    class _gps_sleep_mode(object):
        none = 0x0
        pull_off = 0x1
        backup = 0x2
        standby = 0x3

    profile_idx = 1

    _gps_cfg = {
        "UARTn": UART.UART1,
        "buadrate": 115200,
        "databits": 8,
        "parity": 0,
        "stopbits": 1,
        "flowctl": 0,
        "PowerPin": None,
        "StandbyPin": None,
        "BackupPin": None,
        "gps_mode": _gps_mode.internal
    }

    _cell_cfg = {
        "serverAddr": "www.queclocator.com",
        "port": 80,
        "token": "xGP77d2z0i91s67n",
        "timeout": 3,
        "profileIdx": profile_idx,
    }

    _wifi_cfg = {
        "token": "xGP77d2z0i91s67n"
    }

    loc_method = _loc_method.all

    map_coordinate_system = _map_coordinate_system.WGS84

    gps_sleep_mode = _gps_sleep_mode.none

    locator_init_params = {
        "gps_cfg": _gps_cfg,
        "cell_cfg": _cell_cfg,
        "wifi_cfg": _wifi_cfg,
    }
