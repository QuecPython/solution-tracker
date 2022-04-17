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
