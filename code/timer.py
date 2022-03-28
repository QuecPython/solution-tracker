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

import osTimer

from usr.common import Singleton
from usr.logging import getLogger

log = getLogger(__name__)


class LEDTimer(Singleton):
    def __init__(self, tracker):
        self.period = 500
        self.tracker = tracker
        self.energy_led_count = 0
        self.running_led_count = 0
        self.led_timer = osTimer()
        self.led_timer.start(self.period, 1, self.led_callback)

    def led_callback(self, args):
        self.energy_led_count += 1
        self.running_led_count += 1

        if self.tracker.energy_led.period is not None:
            if self.tracker.energy_led.period == 0 or \
                    (self.tracker.energy_led.period > 0 and int(self.tracker.energy_led.period / self.period) <= self.energy_led_count):
                self.led_switch(self.tracker.energy_led)

        if self.tracker.running_led.period is not None:
            if self.tracker.running_led.period == 0 or \
                    (self.tracker.running_led.period > 0 and int(self.tracker.running_led.period / self.period) <= self.running_led_count):
                self.led_switch(self.tracker.running_led)

    def led_switch(self, led):
        if led.period == 0:
            led.switch(1)
        else:
            led.switch()
