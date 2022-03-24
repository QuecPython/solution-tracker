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

import _thread

from queue import Queue
from usr.common import Singleton
from usr.logging import getLogger

log = getLogger(__name__)


def sensor_process(args):
    self = args
    while True:
        sensor_read = self.sensor_queue.get()
        if sensor_read:
            sensor_data = {}
            sensor_data['temperature'] = self.temperature()
            sensor_data['light'] = self.light()
            sensor_data['driving_behavior_code'] = self.driving_behavior()
            if self.sensor_read_cb:
                self.sensor_read_cb(**sensor_data)
            else:
                log.warn('Sensor read callback is not defined.')


class Sensor(Singleton):
    def __init__(self, sensor_read_cb=None):
        self.sensor_read_cb = sensor_read_cb
        self.sensor_queue = Queue(maxsize=64)
        _thread.start_new_thread(sensor_process, (self,))

    def temperature(self):
        # TODO: Get temperature value
        temperature_values = None
        return temperature_values

    def light(self):
        # TODO: Get temperature value
        light_values = None
        return light_values

    def driving_behavior(self):
        # TODO: Get driving behavior code
        driving_behavior_code = None
        return driving_behavior_code

    def post_data(self, sensor_type, sensor_value):
        self.sensor_queue.put(True)
