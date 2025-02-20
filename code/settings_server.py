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
@file      :dev_settings_server.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :Server config.
@version   :2.2.0
@date      :2022-10-31 14:42:25
@copyright :Copyright (c) 2022
"""


class AliIotConfig:

    product_key = ""
    device_name = ""
    device_secret = ""
    product_secret = None
    server = "iot-as-mqtt.cn-shanghai.aliyuncs.com"
    qos = 1



class ThingsBoardConfig:

    host = ""
    port = 1883
    username = ""
    qos = 0
    client_id = ""
