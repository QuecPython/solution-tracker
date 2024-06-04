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
@file      :net_manage.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :<description>
@version   :1.0.0
@date      :2022-10-31 10:45:46
@copyright :Copyright (c) 2022
"""
import net
import usys
import utime
import ntptime
import dataCall
import checkNet


class NetManage:

    def __init__(self, project_name, project_version):
        self.__checknet = checkNet.CheckNetwork(project_name, project_version)
        self.__checknet.poweron_print_once()

    @property
    def status(self):
        res = False
        try:
            data_call_info = dataCall.getInfo(1, 0)
            res = True if isinstance(data_call_info, tuple) and data_call_info[2][0] == 1 else False
        except Exception as e:
            usys.print_exception(e)
        return res

    def wait_connect(self, timeout=60):
        return self.__checknet.waitNetworkReady(timeout)

    def connect(self):
        if net.setModemFun(1) == 0:
            return True
        return False

    def disconnect(self):
        if net.setModemFun(4) == 0:
            return True
        return False

    def reconnect(self):
        if self.disconnect():
            utime.sleep_ms(200)
            return self.connect()
        return False

    def sync_time(self, timezone=8):
        return True if self.status and ntptime.settime(timezone) == 0 else False
