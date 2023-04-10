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
@file      :settings_cloud.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :<description>
@version   :1.0.0
@date      :2022-10-31 14:42:25
@copyright :Copyright (c) 2022
"""


class AliCloudConfig(object):

    class _burning_method(object):
        one_type_one_secret = 0x0
        one_machine_one_secret = 0x1

    pk = "h3nqn03lil0"
    ps = "UH9muaJIoAlpvnqE"
    dk = "TrackerDevJack"
    ds = "2980b4b86fb011375739a150c23bc252"

    server = "%s.iot-as-mqtt.cn-shanghai.aliyuncs.com" % pk
    client_id = dk
    life_time = 120
    burning_method = _burning_method.one_machine_one_secret


class ThingsBoardConfig:
    host = "111.230.64.210"
    port = 10021
    username = "J2tD4KKfSSi2xpC81RxM"
    quality_of_service = 0
    client_id = "cacc2ac0-3333-11ed-a97b-cdc783a0f67e"
    chunk_size = 0
