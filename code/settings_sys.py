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

import uos
import modem

from machine import UART

from usr.settings_app import default_values_app

PROJECT_NAME = "QuecPython-Tracker"

PROJECT_VERSION = "2.0.1"

DEVICE_FIRMWARE_NAME = uos.uname()[0].split("=")[1]

DEVICE_FIRMWARE_VERSION = modem.getDevFwVersion()

ALERTCODE = {
    20000: "fault_alert",
    30002: "low_power_alert",
    30003: "over_speed_alert",
    30004: "sim_abnormal_alert",
    30005: "disassemble_alert",
    40000: "drive_behavior_alert",
    50001: "sos_alert",
}

LOWENERGYMAP = {
    "EC200U": [
        "POWERDOWN",
        "PM",
    ],
    "EC200U": [
        "POWERDOWN",
        "PM",
    ],
    "EC600N": [
        "PM",
    ],
    "EC800G": [
        "PM"
    ],
}


class default_values_sys(object):
    """
    System default settings
    """

    class _cloud(object):
        none = 0x0
        quecIot = 0x1
        AliYun = 0x2
        JTT808 = 0x4
        customization = 0x8

    class _gps_mode(object):
        none = 0x0
        internal = 0x1
        external = 0x2

    class _drive_behavior_code(object):
        none = 0x0
        quick_start = 0x1
        quick_stop = 0x2
        quick_turn_left = 0x3
        quick_turn_right = 0x4

    class _ota_upgrade_status(object):
        none = 0x0
        to_be_updated = 0x1
        updating = 0x2
        update_successed = 0x3
        update_failed = 0x4

    class _ota_upgrade_module(object):
        none = 0x0
        sys = 0x1
        app = 0x2

    class _ali_burning_method(object):
        one_type_one_density = 0x0
        one_machine_one_density = 0x1

    """
    variables of system default settings below MUST NOT start with "_"
    """
    sw_log = True

    checknet_timeout = 60

    profile_idx = 1

    gps_mode = _gps_mode.external

    ota_status = {}

    user_ota_action = -1

    drive_behavior_code = _drive_behavior_code.none

    cloud = _cloud.quecIot

    cloud_life_time = 120

    cloud_init_params = {}

    work_mode_timeline = 3600

    ali_burning_method = _ali_burning_method.one_machine_one_density

    # trackdev0304 (PROENV)
    _quecIot = {
        "PK": "p11275",
        "PS": "Q0ZQQndaN3pCUFd6",
        "DK": "trackdev0304",
        "DS": "b56c9cf279b146d7d7a48e7e767362d9",
        "SERVER": "iot-south.quectel.com:2883",
    }

    # # trackerdemo0326 (PROENV)
    # _quecIot = {
    #     "PK": "p11275",
    #     "PS": "Q0ZQQndaN3pCUFd6",
    #     "DK": "trackerdemo0326",
    #     "DS": "32d540996e32f95c58dd98f18d473d52",
    #     "SERVER": "iot-south.quectel.com:2883",
    # }

    # # IMEI (PROENV)
    # _quecIot = {
    #     "PK": "p11275",
    #     "PS": "Q0ZQQndaN3pCUFd6",
    #     "DK": "",
    #     "DS": "",
    #     "SERVER": "iot-south.quectel.com:2883",
    # }

    # # TrackerDevEC600NCNLC (TESTENV)
    # _quecIot = {
    #     "PK": "p119v2",
    #     "PS": "TXRPdVVhdkY3bU5s",
    #     "DK": "TrackerDevEC600NCNLC",
    #     "DS": "",
    #     "SERVER": "mqtt://220.180.239.212:8382",
    # }

    # # IMEI (TESTENV)
    # _quecIot = {
    #     "PK": "p119v2",
    #     "PS": "TXRPdVVhdkY3bU5s",
    #     "DK": "",
    #     "DS": "",
    #     "SERVER": "mqtt://220.180.239.212:8382",
    # }

    # tracker_dev_jack
    _AliYun = {
        "PK": "a1q1kmZPwU2",
        "PS": "HQraBqtV8WsfCEuy",
        "DK": "tracker_dev_jack",
        "DS": "bfdfcca5075715e8309eff8597663c4b",
        "SERVER": "a1q1kmZPwU2.iot-as-mqtt.cn-shanghai.aliyuncs.com",
    }

    _JTT808 = {
        "PK": "",
        "PS": "",
        "DK": "",
        "DS": "",
        "SERVER": "",
    }

    locator_init_params = {}

    _gps_cfg = {
        "UARTn": UART.UART1,
        "buadrate": 115200,
        "databits": 8,
        "parity": 0,
        "stopbits": 1,
        "flowctl": 0,
    }

    _cellLocator_cfg = {
        "serverAddr": "www.queclocator.com",
        "port": 80,
        "token": "xGP77d2z0i91s67n",
        "timeout": 3,
        "profileIdx": profile_idx,
    }

    _wifiLocator_cfg = {
        "token": "xGP77d2z0i91s67n"
    }

    @staticmethod
    def _get_locator_init_params(loc_method):
        locator_init_params = {}

        if loc_method & default_values_app._loc_method.gps:
            locator_init_params["gps_cfg"] = default_values_sys._gps_cfg
        if loc_method & default_values_app._loc_method.cell:
            locator_init_params["cellLocator_cfg"] = default_values_sys._cellLocator_cfg
        if loc_method & default_values_app._loc_method.wifi:
            locator_init_params["wifiLocator_cfg"] = default_values_sys._wifiLocator_cfg

        return locator_init_params

    @staticmethod
    def _get_cloud_init_params(cloud):
        cloud_init_params = {}

        if cloud & default_values_sys._cloud.quecIot:
            cloud_init_params = default_values_sys._quecIot
        if cloud & default_values_sys._cloud.AliYun:
            cloud_init_params = default_values_sys._AliYun
        if cloud & default_values_sys._cloud.JTT808:
            cloud_init_params = default_values_sys._JTT808

        return cloud_init_params

    @staticmethod
    def _ota_status_init_params():
        ota_status = {
            "sys_current_version": DEVICE_FIRMWARE_NAME,
            "sys_target_version": "--",
            "app_current_version": PROJECT_VERSION,
            "app_target_version": "--",
            "upgrade_module": default_values_sys._ota_upgrade_module.none,
            "upgrade_status": default_values_sys._ota_upgrade_status.none,
        }

        return ota_status
