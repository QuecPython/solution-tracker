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

import dataCall
from misc import Power

from usr.modules.led import LED
from usr.modules.logging import getLogger
from usr.modules.mpower import LowEnergyManage
from usr.modules.remote import RemotePublish
from usr.modules.common import Singleton
from usr.settings import Settings

try:
    from misc import USB
except ImportError:
    USB = None
try:
    from misc import PowerKey
except ImportError:
    PowerKey = None

log = getLogger(__name__)


class Controller(Singleton):
    """Device module control and post data to cloud"""

    def __init__(self):
        self.__remote_pub = None
        self.__settings = None
        self.__low_energy = None
        self.__energy_led = None
        self.__running_led = None
        self.__power_key = None
        self.__usb = None
        self.__data_call = None

    def add_module(self, module, led_type=None, callback=None):
        if isinstance(module, RemotePublish):
            self.__remote_pub = module
            return True
        elif isinstance(module, Settings):
            self.__settings = module
            return True
        elif isinstance(module, LowEnergyManage):
            self.__low_energy = module
            return True
        elif isinstance(module, LED):
            if led_type == "energy":
                self.__energy_led = module
                return True
            elif led_type == "running":
                self.running_led = module
                return True
        elif isinstance(module, PowerKey):
            self.__power_key = module
            if callback:
                self.__power_key.powerKeyEventRegister(callback)
            return True
        elif isinstance(module, USB):
            self.__usb = module
            if callback:
                self.__usb.setCallback(callback)
            return True
        elif module is dataCall:
            self.__data_call = module
            if callback:
                self.__data_call.setCallback(callback)
            return True

        return False

    def settings_set(self, key, value):
        if not self.__settings:
            raise TypeError("self.__settings is not registered.")
        set_res = self.__settings.set(key, value)
        log.debug("__settings_set key: %s, val: %s, set_res: %s" % (key, value, set_res))
        return set_res

    def settings_save(self):
        if not self.__settings:
            raise TypeError("self.__settings is not registered.")
        return self.__settings.save()

    def power_restart(self):
        Power.powerRestart()

    def power_down(self):
        Power.powerDown()

    def remote_post_data(self, data):
        if not self.__remote_pub:
            raise TypeError("self.__remote_pub is not registered.")
        log.debug("remote_post_data data: %s" % str(data))
        return self.__remote_pub.post_data(data)

    def remote_ota_check(self):
        if not self.__remote_pub:
            raise TypeError("self.__remote_pub is not registered.")
        return self.__remote_pub.cloud_ota_check()

    def remote_ota_action(self, action, module):
        if not self.__remote_pub:
            raise TypeError("self.__remote_pub is not registered.")
        return self.__remote_pub.cloud_ota_action(action, module)

    def remote_device_report(self):
        if not self.__remote_pub:
            raise TypeError("self.__remote_pub is not registered.")
        return self.__remote_pub.cloud_device_report()

    def remote_rrpc_response(self, message_id, data):
        if not self.__remote_pub:
            raise TypeError("self.__remote_pub is not registered.")
        return self.__remote_pub.cloud_rrpc_response(message_id, data)

    def low_energy_set_period(self, period):
        if not self.__low_energy:
            raise TypeError("self.__low_energy is not registered.")
        return self.__low_energy.set_period(period)

    def low_energy_set_method(self, method):
        if not self.__low_energy:
            raise TypeError("self.__low_energy is not registered.")
        return self.__low_energy.set_low_energy_method(method)

    def low_energy_init(self):
        if not self.__low_energy:
            raise TypeError("self.__low_energy is not registered.")
        return self.__low_energy.low_energy_init()

    def low_energy_start(self):
        if not self.__low_energy:
            raise TypeError("self.__low_energy is not registered.")
        return self.__low_energy.start()

    def low_energy_stop(self):
        if not self.__low_energy:
            raise TypeError("self.__low_energy is not registered.")
        return self.__low_energy.stop()

    def running_led_show(self, on_period, off_period):
        if not self.__running_led:
            raise TypeError("self.__running_led is not registered.")
        return self.__running_led.start_flicker(on_period, off_period)

    def energy_led_show(self, on_period, off_period):
        if not self.energy_led_show:
            raise TypeError("self.energy_led_show is not registered.")
        return self.__energy_led.start_flicker(on_period, off_period)
