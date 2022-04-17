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


class QuecCloudConfig(object):
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

    # trackdev0304 (PROENV)
    PK = "p11275"
    PS = "Q0ZQQndaN3pCUFd6"
    DK = "trackdev0304"
    DS = ""

    # # trackerdemo0326 (PROENV)
    # "PK": "p11275",
    # "PS": "Q0ZQQndaN3pCUFd6",
    # "DK": "trackerdemo0326",
    # "DS": "",

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
