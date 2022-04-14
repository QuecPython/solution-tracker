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
import ure
import ql_fs
import ujson
import modem
import _thread
from machine import UART

from usr.common import Singleton
from usr.common import option_lock


PROJECT_NAME = "QuecPython-Tracker"

PROJECT_VERSION = "2.1.0"

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

cloud_object_model = {
    "event": {
        "event_key": {
            "id": 1,
            "perm": "",
            "struct_info": {
                "struct_key": {
                    "id": 1
                }
            }
        }
    },
    "property": {
        "property_key": {
            "id": 1,
            "perm": "",
            "struct_info": {
                "struct_key": {
                    "id": 1
                }
            }
        }
    }
}

_settings_lock = _thread.allocate_lock()


class SYSConfig(object):

    class _cloud(object):
        none = 0x0
        quecIot = 0x1
        AliYun = 0x2
        JTT808 = 0x4
        customization = 0x8

    debug = True

    log_level = "DEBUG"

    cloud = _cloud.AliYun

    checknet_timeout = 60

    base_cfg = {
        "LocConfig": True,
    }

    user_cfg = True


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

    profile_idx = 1

    _gps_cfg = {
        "UARTn": UART.UART1,
        "buadrate": 115200,
        "databits": 8,
        "parity": 0,
        "stopbits": 1,
        "flowctl": 0,
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

    gps_mode = _gps_mode.external

    loc_method = _loc_method.gps

    locator_init_params = {
        "gps_cfg": _gps_cfg,
        "cell_cfg": _cell_cfg,
        "wifi_cfg": _wifi_cfg,
    }


class AliConfig(object):

    class _burning_method(object):
        one_type_one_density = 0x0
        one_machine_one_density = 0x1

    PK = "a1q1kmZPwU2"
    PS = "HQraBqtV8WsfCEuy"
    DK = "tracker_dev_jack"
    DS = "bfdfcca5075715e8309eff8597663c4b"

    SERVER = "a1q1kmZPwU2.iot-as-mqtt.cn-shanghai.aliyuncs.com"
    life_time = 120
    burning_method = _burning_method.one_machine_one_density

    object_model = {
        "event": {
            "sos_alert": {
                "id": "",
                "struct_info": {},
            },
            "fault_alert": {
                "id": "",
                "struct_info": {},
            },
            "low_power_alert": {
                "id": "",
                "struct_info": {},
            },
            "sim_abnormal_alert": {
                "id": "",
                "struct_info": {},
            },
            "disassemble_alert": {
                "id": "",
                "struct_info": {},
            },
            "drive_behavior_alert": {
                "id": "",
                "struct_info": {},
            },
            "over_speed_alert": {
                "id": "",
                "struct_info": {},
            },
        },
        "property": {
            "power_switch": {
                "id": "",
                "struct_info": {}
            },
            "energy": {
                "id": "",
                "struct_info": {}
            },
            "phone_num": {
                "id": "",
                "struct_info": {}
            },
            "loc_method": {
                "id": "",
                "struct_info": {
                    "gps": {
                        "id": 1
                    },
                    "cell": {
                        "id": 2
                    },
                    "wifi": {
                        "id": 3
                    },
                },
            },
            "work_mode": {
                "id": "",
                "struct_info": {}
            },
            "work_cycle_period": {
                "id": "",
                "struct_info": {}
            },
            "local_time": {
                "id": "",
                "struct_info": {}
            },
            "low_power_alert_threshold": {
                "id": "",
                "struct_info": {}
            },
            "low_power_shutdown_threshold": {
                "id": "",
                "struct_info": {}
            },
            "sw_ota": {
                "id": "",
                "struct_info": {}
            },
            "sw_ota_auto_upgrade": {
                "id": "",
                "struct_info": {}
            },
            "sw_voice_listen": {
                "id": "",
                "struct_info": {}
            },
            "sw_voice_record": {
                "id": "",
                "struct_info": {}
            },
            "sw_fault_alert": {
                "id": "",
                "struct_info": {}
            },
            "sw_low_power_alert": {
                "id": "",
                "struct_info": {}
            },
            "sw_over_speed_alert": {
                "id": "",
                "struct_info": {}
            },
            "sw_sim_abnormal_alert": {
                "id": "",
                "struct_info": {}
            },
            "sw_disassemble_alert": {
                "id": "",
                "struct_info": {}
            },
            "sw_drive_behavior_alert": {
                "id": "",
                "struct_info": {}
            },
            "drive_behavior_code": {
                "id": "",
                "struct_info": {}
            },
            "power_restart": {
                "id": "",
                "struct_info": {}
            },
            "over_speed_threshold": {
                "id": "",
                "struct_info": {}
            },
            "device_module_status": {
                "id": "",
                "struct_info": {
                    "net": {
                        "id": 1
                    },
                    "location": {
                        "id": 2
                    },
                    "temp_sensor": {
                        "id": 3
                    },
                    "light_sensor": {
                        "id": 4
                    },
                    "move_sensor": {
                        "id": 5
                    },
                    "mike": {
                        "id": 6
                    },
                }
            },
            "gps_mode": {
                "id": "",
                "struct_info": {}
            },
            "user_ota_action": {
                "id": "",
                "struct_info": {}
            },
            "ota_status": {
                "id": "",
                "struct_info": {
                    "sys_current_version": {
                        "id": 1
                    },
                    "sys_target_version": {
                        "id": 2
                    },
                    "app_current_version": {
                        "id": 3
                    },
                    "app_target_version": {
                        "id": 4
                    },
                    "upgrade_module": {
                        "id": 5
                    },
                    "upgrade_status": {
                        "id": 6
                    },
                },
            },
            "GeoLocation": {
                "id": "",
                "struct_info": {}
            },
            "voltage": {
                "id": "",
                "struct_info": {
                    "Longitude": {
                        "id": 1
                    },
                    "Latitude": {
                        "id": 2
                    },
                    "Altitude": {
                        "id": 3
                    },
                    "CoordinateSystem": {
                        "id": 4
                    }
                }
            },
            "current_speed": {
                "id": "",
                "struct_info": {}
            }
        },
    }


class QuecConfig(object):
    # trackdev0304 (PROENV)
    PK = "p11275"
    PS = "Q0ZQQndaN3pCUFd6"
    DK = "trackdev0304"
    DS = "b56c9cf279b146d7d7a48e7e767362d9"

    # # trackerdemo0326 (PROENV)
    # "PK": "p11275",
    # "PS": "Q0ZQQndaN3pCUFd6",
    # "DK": "trackerdemo0326",
    # "DS": "32d540996e32f95c58dd98f18d473d52",

    # # IMEI (PROENV)
    # "PK": "p11275",
    # "PS": "Q0ZQQndaN3pCUFd6",
    # "DK": "",
    # "DS": "",

    # # TrackerDevEC600NCNLC (TESTENV)
    # "PK": "p119v2",
    # "PS": "TXRPdVVhdkY3bU5s",
    # "DK": "TrackerDevEC600NCNLC",
    # "DS": "",

    # # IMEI (TESTENV)
    # "PK": "p119v2",
    # "PS": "TXRPdVVhdkY3bU5s",
    # "DK": "",
    # "DS": "",

    SERVER = "iot-south.quectel.com:1883"
    life_time = 120

    object_model = {
        "event": {
            "sos_alert": {
                "id": 6,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
            "fault_alert": {
                "id": 14,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
            "low_power_alert": {
                "id": 17,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
            "sim_abnormal_alert": {
                "id": 18,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
            "disassemble_alert": {
                "id": 20,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
            "drive_behavior_alert": {
                "id": 22,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
            "over_speed_alert": {
                "id": 35,
                "perm": "r",
                "struct_info": {
                    "local_time": {
                        "id": 19
                    }
                }
            },
        },
        "property": {
            "power_switch": {
                "id": 9,
                "perm": "rw",
                "struct_info": {}
            },
            "energy": {
                "id": 4,
                "perm": "r",
                "struct_info": {}
            },
            "phone_num": {
                "id": 23,
                "perm": "rw",
                "struct_info": {}
            },
            "loc_method": {
                "id": 24,
                "perm": "rw",
                "struct_info": {
                    "gps": {
                        "id": 1
                    },
                    "cell": {
                        "id": 2
                    },
                    "wifi": {
                        "id": 3
                    },
                },
            },
            "work_mode": {
                "id": 25,
                "perm": "rw",
                "struct_info": {}
            },
            "work_cycle_period": {
                "id": 26,
                "perm": "rw",
                "struct_info": {}
            },
            "local_time": {
                "id": 19,
                "perm": "r",
                "struct_info": {}
            },
            "low_power_alert_threshold": {
                "id": 15,
                "perm": "rw",
                "struct_info": {}
            },
            "low_power_shutdown_threshold": {
                "id": 16,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_ota": {
                "id": 12,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_ota_auto_upgrade": {
                "id": 13,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_voice_listen": {
                "id": 10,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_voice_record": {
                "id": 11,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_fault_alert": {
                "id": 27,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_low_power_alert": {
                "id": 28,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_over_speed_alert": {
                "id": 29,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_sim_abnormal_alert": {
                "id": 30,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_disassemble_alert": {
                "id": 31,
                "perm": "rw",
                "struct_info": {}
            },
            "sw_drive_behavior_alert": {
                "id": 32,
                "perm": "rw",
                "struct_info": {}
            },
            "drive_behavior_code": {
                "id": 21,
                "perm": "r",
                "struct_info": {}
            },
            "power_restart": {
                "id": 33,
                "perm": "w",
                "struct_info": {}
            },
            "over_speed_threshold": {
                "id": 34,
                "perm": "rw",
                "struct_info": {}
            },
            "device_module_status": {
                "id": 36,
                "perm": "r",
                "struct_info": {
                    "net": {
                        "id": 1
                    },
                    "location": {
                        "id": 2
                    },
                    "temp_sensor": {
                        "id": 3
                    },
                    "light_sensor": {
                        "id": 4
                    },
                    "move_sensor": {
                        "id": 5
                    },
                    "mike": {
                        "id": 6
                    },
                }
            },
            "gps_mode": {
                "id": 37,
                "perm": "r",
                "struct_info": {}
            },
            "user_ota_action": {
                "id": 38,
                "perm": "w",
                "struct_info": {}
            },
            "voltage": {
                "id": 41,
                "perm": "r",
                "struct_info": {}
            },
            "ota_status": {
                "id": 42,
                "perm": "r",
                "struct_info": {
                    "sys_current_version": {
                        "id": 1
                    },
                    "sys_target_version": {
                        "id": 2
                    },
                    "app_current_version": {
                        "id": 3
                    },
                    "app_target_version": {
                        "id": 4
                    },
                    "upgrade_module": {
                        "id": 5
                    },
                    "upgrade_status": {
                        "id": 6
                    },
                },
            },
            "current_speed": {
                "id": 43,
                "perm": "r",
                "struct_info": {}
            }
        }
    }


class JTT808Config(object):
    PK = ""
    PS = ""
    DK = ""
    DS = ""
    SERVER = ""
    life_time = 120
    object_model = {
        "event": {},
        "property": {},
    }


class UserConfig(object):

    class _work_mode(object):
        cycle = 0x1
        intelligent = 0x2

    class _drive_behavior_code(object):
        none = 0x0
        sharply_start = 0x1
        sharply_stop = 0x2
        sharply_turn_left = 0x3
        sharply_turn_right = 0x4

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

    phone_num = ""

    low_power_alert_threshold = 20

    low_power_shutdown_threshold = 5

    over_speed_threshold = 50

    sw_ota = True

    sw_ota_auto_upgrade = True

    sw_voice_listen = False

    sw_voice_record = False

    sw_fault_alert = True

    sw_low_power_alert = True

    sw_over_speed_alert = True

    sw_sim_abnormal_alert = True

    sw_disassemble_alert = True

    sw_drive_behavior_alert = True

    drive_behavior_code = _drive_behavior_code.none

    loc_method = LocConfig._loc_method.gps

    work_mode = _work_mode.cycle

    work_mode_timeline = 3600

    work_cycle_period = 30

    user_ota_action = -1

    ota_status = {
        "sys_current_version": DEVICE_FIRMWARE_NAME,
        "sys_target_version": "--",
        "app_current_version": PROJECT_VERSION,
        "app_target_version": "--",
        "upgrade_module": _ota_upgrade_module.none,
        "upgrade_status": _ota_upgrade_status.none,
    }


class Settings(Singleton):

    def __init__(self, settings_file="/usr/tracker_settings.json"):
        self.settings_file = settings_file
        self.current_settings = {}
        self.init()

    @option_lock(_settings_lock)
    def init(self):
        if ql_fs.path_exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                self.current_settings = ujson.load(f)
            return True

        self.current_settings["sys"] = {k: v for k, v in SYSConfig.__dict__.items() if not k.startswith("_")}

        if self.current_settings["sys"]["cloud"] == SYSConfig._cloud.AliYun:
            self.current_settings["cloud"] = {k: v for k, v in AliConfig.__dict__.items() if not k.startswith("_")}
        elif self.current_settings["sys"]["cloud"] == SYSConfig._cloud.quecIot:
            self.current_settings["cloud"] = {k: v for k, v in QuecConfig.__dict__.items() if not k.startswith("_")}
        elif self.current_settings["sys"]["cloud"] == SYSConfig._cloud.JTT808:
            self.current_settings["cloud"] = {k: v for k, v in JTT808Config.__dict__.items() if not k.startswith("_")}
        elif self.current_settings["sys"]["cloud"] == SYSConfig._cloud.customization:
            self.current_settings["cloud"] = {}
        else:
            self.current_settings["cloud"] = {}

        if self.current_settings["sys"]["base_cfg"]["LocConfig"]:
            self.current_settings["LocConfig"] = {k: v for k, v in LocConfig.__dict__.items() if not k.startswith("_")}

        if self.current_settings["sys"]["user_cfg"]:
            self.current_settings["user_cfg"] = {k: v for k, v in UserConfig.__dict__.items() if not k.startswith("_")}

        with open(self.settings_file, "w") as f:
            ujson.dump(self.current_settings, f)

        return True

    @option_lock(_settings_lock)
    def get(self):
        return self.current_settings

    @option_lock(_settings_lock)
    def set(self, opt, val):
        if opt in self.current_settings["user_cfg"]:
            if opt == "phone_num":
                if not isinstance(val, str):
                    return False
                pattern = ure.compile(r"^(?:(?:\+)86)?1[3-9]\d\d\d\d\d\d\d\d\d$")
                if pattern.search(val):
                    self.current_settings["user_cfg"][opt] = val
                    return True
                return False
            elif opt == "loc_method":
                if not isinstance(val, int):
                    return False
                if val > LocConfig._loc_method.all:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt == "work_mode":
                if not isinstance(val, int):
                    return False
                if val > UserConfig._work_mode.intelligent:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("work_cycle_period", "over_speed_threshold"):
                if not isinstance(val, int):
                    return False
                if val < 1:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("low_power_alert_threshold", "low_power_shutdown_threshold"):
                if not isinstance(val, int):
                    return False
                if val < 0 or val > 100:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("sw_ota", "sw_ota_auto_upgrade", "sw_voice_listen", "sw_voice_record",
                         "sw_fault_alert", "sw_low_power_alert", "sw_over_speed_alert",
                         "sw_sim_abnormal_alert", "sw_disassemble_alert", "sw_drive_behavior_alert"):
                if not isinstance(val, bool):
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt == "ota_status":
                if not isinstance(val, dict):
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("user_ota_action", "drive_behavior_code"):
                if not isinstance(val, int):
                    return False
                self.current_settings["sys"][opt] = val
                return True
        elif opt == "cloud":
            if not isinstance(val, dict):
                return False
            self.current_settings[opt] = val
            return True

        return False

    @option_lock(_settings_lock)
    def save(self):
        try:
            with open(self.settings_file, "w") as f:
                ujson.dump(self.current_settings, f)
            return True
        except:
            return False

    @option_lock(_settings_lock)
    def reset(self):
        try:
            uos.remove(self.settings_file)
            return True
        except:
            return False


settings = Settings()
