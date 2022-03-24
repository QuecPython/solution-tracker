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
from misc import Power


class Singleton(object):
    _instance_lock = _thread.allocate_lock()

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance_dict'):
            Singleton.instance_dict = {}

        if str(cls) not in Singleton.instance_dict.keys():
            with Singleton._instance_lock:
                _instance = super().__new__(cls)
                Singleton.instance_dict[str(cls)] = _instance

        return Singleton.instance_dict[str(cls)]


def numiter():
    for i in range(99999):
        yield i


def power_restart():
    Power.powerRestart()
