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

LOWENERGYMAP = {
    "EC200U": [
        "POWERDOWN",
        "PM",
    ],
    "EC200U": [
        "POWERDOWN",
        "PM",
    ],
    "EC600N": [
        "PM",
    ],
    "EC800G": [
        "PM"
    ],
}


def numiter(num=99999):
    for i in range(num):
        yield i


def option_lock(thread_lock):
    def function_lock(func):
        def wrapperd_fun(*args, **kwargs):
            with thread_lock:
                return func(*args, **kwargs)
        return wrapperd_fun
    return function_lock


class BaseError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Singleton(object):
    _instance_lock = _thread.allocate_lock()

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance_dict"):
            Singleton.instance_dict = {}

        if str(cls) not in Singleton.instance_dict.keys():
            with Singleton._instance_lock:
                _instance = super().__new__(cls)
                Singleton.instance_dict[str(cls)] = _instance

        return Singleton.instance_dict[str(cls)]


class Observer(object):

    def update(self, observable, *args, **kwargs):
        pass


class Observable(Singleton):

    def __init__(self):
        self.__observers = []

    def addObserver(self, observer):
        try:
            self.__observers.append(observer)
            return True
        except:
            return False

    def delObserver(self, observer):
        try:
            self.__observers.remove(observer)
            return True
        except:
            return False

    def notifyObservers(self, *args, **kwargs):
        for o in self.__observers:
            o.update(self, *args, **kwargs)


class CloudObserver(object):

    def execute(self, observable, *args, **kwargs):
        pass


class CloudObservable(Singleton):

    def __init__(self):
        self.__observers = []

    def addObserver(self, observer):
        self.__observers.append(observer)

    def delObserver(self, observer):
        self.__observers.remove(observer)

    def notifyObservers(self, *args, **kwargs):
        for o in self.__observers:
            o.execute(self, *args, **kwargs)

    def init(self, enforce=False):
        pass

    def close(self):
        pass

    def post_data(self, data):
        pass

    def ota_request(self, *args, **kwargs):
        pass

    def ota_action(self, action, module=None):
        pass


class CloudObjectModel(Singleton):

    def __init__(self):
        self.items = {
            "event": {},
            "property": {},
        }

    def set_item(self, om_type, om_key, om_key_id=None, om_key_perm=None):
        om_data = {
            "name": om_key,
            "id": om_key_id,
            "perm": om_key_perm,
            "struct_info": {}
        }
        if self.items.get(om_type) is not None:
            self.items[om_type][om_key] = om_data
            return True
        return False

    def del_item(self, om_type, om_key):
        if self.items.get(om_type) is not None:
            if self.items[om_type].get(om_key) is not None:
                self.items[om_type].pop(om_key)
                return True
        return False

    def set_item_struct(self, om_type, om_key, struct_key, struct_key_id=None, struct_key_struct=None):
        if self.items.get(om_type) is not None:
            if self.items[om_type].get(om_key) is not None:
                if self.items[om_type][om_key].get("struct_info") is None:
                    self.items[om_type][om_key]["struct_info"] = {}
                self.items[om_type][om_key]["struct_info"][struct_key] = {
                    "name": struct_key,
                    "id": struct_key_id,
                    "struct_info": struct_key_struct,
                }
                return True
        return False
