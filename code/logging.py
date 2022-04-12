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

import utime


class Logger:
    def __init__(self, name):
        self.name = name
        self.__debug = True
        self.__level = "debug"
        self.__level_code = {
            "debug": 0,
            "info": 1,
            "warn": 2,
            "error": 3,
            "critical": 4,
        }

    def get_debug(self):
        return self.__debug

    def set_debug(self, debug):
        if isinstance(debug, bool):
            self.__debug = debug
            return True
        return False

    def get_level(self):
        return self.__level

    def set_level(self, level):
        if self.__level_code.get(level) is not None:
            self.__level = level
            return True
        return False

    def log(self, name, level, *message):
        if self.__debug is False:
            if self.__level_code.get(level) < self.__level_code.get(self.__level):
                return

        if hasattr(utime, "strftime"):
            print(
                "[{}]".format(utime.strftime("%Y-%m-%d %H:%M:%S")),
                "[{}]".format(name),
                "[{}]".format(level),
                *message
            )
        else:
            t = utime.localtime()
            print(
                "[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]".format(*t),
                "[{}]".format(name),
                "[{}]".format(level),
                *message
            )

    def critical(self, *message):
        self.log(self.name, "critical", *message)

    def error(self, *message):
        self.log(self.name, "error", *message)

    def warn(self, *message):
        self.log(self.name, "warn", *message)

    def info(self, *message):
        self.log(self.name, "info", *message)

    def debug(self, *message):
        self.log(self.name, "debug", *message)


def getLogger(name):
    return Logger(name)
