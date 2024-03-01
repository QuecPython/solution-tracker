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
@file      :settings_loc.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :Loction config.
@version   :2.2.0
@date      :2023-04-11 11:26:16
@copyright :Copyright (c) 2022
"""

from machine import UART


class LocConfig:

    class _gps_mode:
        internal = 0x1
        external_uart = 0x2
        external_i2c = 0x3

    class _map_coordinate_system:
        WGS84 = "WGS84"
        GCJ02 = "GCJ02"

    class _gps_sleep_mode:
        none = 0x0
        pull_off = 0x1
        backup = 0x2
        standby = 0x3

    profile_idx = 1

    map_coordinate_system = _map_coordinate_system.WGS84

    gps_sleep_mode = _gps_sleep_mode.none

    gps_cfg = {
        "UARTn": UART.UART1,
        "buadrate": 115200,
        "databits": 8,
        "parity": 0,
        "stopbits": 1,
        "flowctl": 0,
        "gps_mode": _gps_mode.external_uart,
        "PowerPin": None,
        "StandbyPin": None,
        "BackupPin": None,
    }

    cell_cfg = {
        "serverAddr": "www.queclocator.com",
        "port": 80,
        "token": "xxxxxxxxxx",
        "timeout": 3,
        "profileIdx": profile_idx,
    }

    wifi_cfg = {
        "token": "xxxxxxxxxx"
    }
