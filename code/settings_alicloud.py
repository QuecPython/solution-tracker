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


class AliCloudConfig(object):
    """
    object model data format:

    object_model = {
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
    """

    class _burning_method(object):
        one_type_one_density = 0x0
        one_machine_one_density = 0x1

    PK = "a1q1kmZPwU2"
    PS = "HQraBqtV8WsfCEuy"
    DK = "tracker_dev_jack"
    DS = "bfdfcca5075715e8309eff8597663c4b"

    SERVER = "a1q1kmZPwU2.iot-as-mqtt.cn-shanghai.aliyuncs.com"
    client_id = ""
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
                "struct_info": {
                    "Longtitude": {
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
