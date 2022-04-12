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

    def do_event(self, observable, *args, **kwargs):
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
            o.do_event(self, *args, **kwargs)

    def cloud_init(self, enforce=False):
        pass

    def post_data(self, data):
        pass

    def ota_request(self, *args, **kwargs):
        pass

    def ota_action(self, action, module=None):
        pass
