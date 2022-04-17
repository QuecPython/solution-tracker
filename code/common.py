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
    """Number generation iterator"""
    for i in range(num):
        yield i


def option_lock(thread_lock):
    """Function thread lock decorator"""
    def function_lock(func):
        def wrapperd_fun(*args, **kwargs):
            with thread_lock:
                return func(*args, **kwargs)
        return wrapperd_fun
    return function_lock


class BaseError(Exception):
    """Exception base class"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Singleton(object):
    """Singleton base class"""
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
    """Observer base class"""

    def update(self, observable, *args, **kwargs):
        pass


class Observable(Singleton):
    """Observable base class"""

    def __init__(self):
        self.__observers = []

    def addObserver(self, observer):
        """Add observer"""
        try:
            self.__observers.append(observer)
            return True
        except:
            return False

    def delObserver(self, observer):
        """Delete observer"""
        try:
            self.__observers.remove(observer)
            return True
        except:
            return False

    def notifyObservers(self, *args, **kwargs):
        """Notify observer"""
        for o in self.__observers:
            o.update(self, *args, **kwargs)


class CloudObserver(object):
    """Cloud observer base class"""

    def execute(self, observable, *args, **kwargs):
        pass


class CloudObservable(Singleton):
    """Cloud observable base class"""

    def __init__(self):
        self.__observers = []

    def addObserver(self, observer):
        """Add observer"""
        self.__observers.append(observer)

    def delObserver(self, observer):
        """Delete observer"""
        self.__observers.remove(observer)

    def notifyObservers(self, *args, **kwargs):
        """Notify observer"""
        for o in self.__observers:
            o.execute(self, *args, **kwargs)

    def init(self, enforce=False):
        """Cloud init"""
        pass

    def close(self):
        """Cloud disconnect"""
        pass

    def post_data(self, data):
        """Cloud publish data"""
        pass

    def ota_request(self, *args, **kwargs):
        """Cloud publish ota plain request"""
        pass

    def ota_action(self, action, module=None):
        """Cloud publish ota upgrade or not request"""
        pass


class CloudObjectModel(Singleton):
    """This is a cloud object model base class

    Attribute:
        items: object model dictionary, default two keys
            events: object model events
            property: object model property

        items data format:
        {
            "events": {
                "name": "events",
                "id": "",
                "perm": "rw",
                "struct_info": {
                    "name": "struct",
                    "id": "",
                    "struct_info": {
                        "key": {
                            "name": "key"
                        }
                    },
                },
            },
            "property": {
                "name": "event",
                "id": "",
                "perm": "rw",
                "struct_info": {}
            }
        }
    """

    def __init__(self, om_file):
        self.items = {
            "events": {},
            "properties": {},
        }
        self.om_file = om_file

    def init(self):
        pass

    def set_item(self, om_type, om_key, om_key_id=None, om_key_perm=None):
        """ Set object model item

        Parameter:
            om_type: object model type
                - e.g.: `events`, `properties`

            om_key: object model code
                - e.g.: `local_time`, `speed`, `GeoLocation`

            om_key_id: object model id, not necessary, necessary for quecthing.

            om_key_perm: object model permission, not necessary
                - e.g.: `rw`, `w`, `r`

        Return:
            True: Success
            False: Failed
        """
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
        """Delete object model item

        Parameter:
            om_type: object model type
            om_key: object model code

        Return:
            True: Success
            False: Failed
        """
        if self.items.get(om_type) is not None:
            if self.items[om_type].get(om_key) is not None:
                self.items[om_type].pop(om_key)
                return True
        return False

    def set_item_struct(self, om_type, om_key, struct_key, struct_key_id=None, struct_key_struct=None):
        """Set object model item struct

        Parameter:
            om_type: object model type
            om_key: object model code
            struct_key: object model item struct key name
            struct_key_id: object model item struct key id, not necessary
            struct_key_struct: object model item struct key struct, not necessary

        Return:
            True: Success
            False: Failed
        """
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
