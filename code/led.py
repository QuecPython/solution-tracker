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

# from machine import Pin
from usr.logging import getLogger

log = getLogger(__name__)


class LED(object):
    def __init__(self, period=None):
        self.period = None
        self.led_status = None

    def switch(self, flag=None):
        # TODO:
        # 1. flag is None Auto Check LED Status ON To OFF or OFF To ON.
        # 2. flag is 1 LED ON.
        # 3. flag is 0 LED OFF.
        if flag is None:
            if self.led_status == 1:
                # TODO: LED SET OFF
                self.led_status = 0
            else:
                # TODO: LED SET ON
                self.led_status = 1
        elif flag == 0:
            if self.led_status == 0:
                # TODO: LED ALREADY OFF
                pass
            else:
                # TODO: LED SET OFF
                self.led_status = 0
        elif flag == 1:
            if self.led_status == 1:
                # TODO: LED ALREADY ON
                pass
            else:
                # TODO: LED SET ON
                self.led_status = 1
        pass
