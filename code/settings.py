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

"""
@file      :settings.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :Project settings.
@version   :2.2.0
@date      :2022-10-31 14:42:25
@copyright :Copyright (c) 2022
"""

import uos
import ql_fs
import modem
import _thread
import usys as sys

try:
    from settings_server import AliIotConfig, ThingsBoardConfig
    from settings_loc import LocConfig
    from settings_user import UserConfig
except ImportError:
    from usr.settings_server import AliIotConfig, ThingsBoardConfig
    from usr.settings_loc import LocConfig
    from usr.settings_user import UserConfig

PROJECT_NAME = "QuecPython-Tracker"

PROJECT_VERSION = "2.2.0"

FIRMWARE_NAME = uos.uname()[0].split("=")[1]

FIRMWARE_VERSION = modem.getDevFwVersion()

class Settings:

    def __init__(self, config_file="/usr/tracker_config.json"):
        self.__file = config_file
        self.__lock = _thread.allocate_lock()
        self.__data = {}
        self.__init_config()

    def __init_config(self):
        try:
            if ql_fs.path_exists(self.__file):
                ql_fs.touch(self.__file, {})

            # UserConfig init
            self.__data["user"] = {k: v for k, v in UserConfig.__dict__.items() if not k.startswith("_")}
            self.__data["user"]["ota_status"]["sys_current_version"] = FIRMWARE_VERSION
            self.__data["user"]["ota_status"]["app_current_version"] = PROJECT_VERSION

            # CloudConfig init
            self.__data["server"] = {}
            if self.__data["user"]["server"] == UserConfig._server.AliIot:
                self.__data["server"] = {k: v for k, v in AliIotConfig.__dict__.items() if not k.startswith("_")}
            elif self.__data["user"]["server"] == UserConfig._server.ThingsBoard:
                self.__data["server"] = {k: v for k, v in ThingsBoardConfig.__dict__.items() if not k.startswith("_")}

            # LocConfig init
            self.__data["loc"] = {k: v for k, v in LocConfig.__dict__.items() if not k.startswith("_")}
            ql_fs.touch(self.__file, self.__data)
        except Exception as e:
            sys.print_exception(e)

    def read(self, key=None):
        with self.__lock:
            try:
                return self.__data if key is None else self.__data.get(key)
            except Exception as e:
                sys.print_exception(e)

    def save(self, data):
        with self.__lock:
            res = -1
            if isinstance(data, dict):
                self.__data.update(data)
                res = ql_fs.touch(self.__file, self.__data)
            return True if res == 0 else False
