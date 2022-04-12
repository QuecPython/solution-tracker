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

quec_object_model = {
    # property
    9: ("power_switch", "rw"),
    4: ("energy", "r"),
    23: ("phone_num", "rw"),
    24: ("loc_method", "rw"),
    25: ("work_mode", "rw"),
    26: ("work_cycle_period", "rw"),
    19: ("local_time", "r"),
    15: ("low_power_alert_threshold", "rw"),
    16: ("low_power_shutdown_threshold", "rw"),
    12: ("sw_ota", "rw"),
    13: ("sw_ota_auto_upgrade", "rw"),
    10: ("sw_voice_listen", "rw"),
    11: ("sw_voice_record", "rw"),
    27: ("sw_fault_alert", "rw"),
    28: ("sw_low_power_alert", "rw"),
    29: ("sw_over_speed_alert", "rw"),
    30: ("sw_sim_abnormal_alert", "rw"),
    31: ("sw_disassemble_alert", "rw"),
    32: ("sw_drive_behavior_alert", "rw"),
    21: ("drive_behavior_code", "r"),
    33: ("power_restart", "w"),
    34: ("over_speed_threshold", "rw"),
    36: ("device_module_status", "r"),
    37: ("gps_mode", "r"),
    38: ("user_ota_action", "w"),
    41: ("voltage", "r"),
    42: ("ota_status", "r"),
    43: ("current_speed", "r"),

    # event
    6:  ("sos_alert", "r"),
    14: ("fault_alert", "r"),
    17: ("low_power_alert", "r"),
    18: ("sim_abnormal_alert", "r"),
    20: ("disassemble_alert", "r"),
    22: ("drive_behavior_alert", "r"),
    35: ("over_speed_alert", "r"),
}

quec_object_model_struct = {
    "device_module_status": {
        "net": 1,
        "location": 2,
        "temp_sensor": 3,
        "light_sensor": 4,
        "move_sensor": 5,
        "mike": 6,
    },
    "loc_method": {
        "gps": 1,
        "cell": 2,
        "wifi": 3,
    },
    "ota_status": {
        "sys_current_version": 1,
        "sys_target_version": 2,
        "app_current_version": 3,
        "app_target_version": 4,
        "upgrade_module": 5,
        "upgrade_status": 6,
    },
}

ali_object_model = {
    "event": [
        "sos_alert",
        "fault_alert",
        "low_power_alert",
        "sim_abnormal_alert",
        "disassemble_alert",
        "drive_behavior_alert",
        "over_speed_alert",
    ],
    "property": [
        "power_switch",
        "energy",
        "phone_num",
        "loc_method",
        "work_mode",
        "work_cycle_period",
        "local_time",
        "low_power_alert_threshold",
        "low_power_shutdown_threshold",
        "sw_ota",
        "sw_ota_auto_upgrade",
        "sw_voice_listen",
        "sw_voice_record",
        "sw_fault_alert",
        "sw_low_power_alert",
        "sw_over_speed_alert",
        "sw_sim_abnormal_alert",
        "sw_disassemble_alert",
        "sw_drive_behavior_alert",
        "drive_behavior_code",
        "power_restart",
        "over_speed_threshold",
        "device_module_status",
        "gps_mode",
        "user_ota_action",
        "ota_status",
        "GeoLocation",
        "voltage",
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
