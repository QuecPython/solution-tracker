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

import uos
import ure
import ql_fs
import ujson
import modem
import _thread

from usr import settings_cloud
from usr.settings_loc import LocConfig
from usr.settings_user import UserConfig
from usr.modules.common import Singleton, option_lock

PROJECT_NAME = "QuecPython-Tracker"

PROJECT_VERSION = "2.2.0"

DEVICE_FIRMWARE_NAME = uos.uname()[0].split("=")[1]

DEVICE_FIRMWARE_VERSION = modem.getDevFwVersion()

LOWENERGYMAP = {
    "PM": ["EC200U", "EC600N", "EC800G", "EC800M"],
    "POWERDOWN": ["EC200U"],
}

_settings_lock = _thread.allocate_lock()


class Settings(Singleton):

    def __init__(self, settings_file="/usr/tracker_settings.json"):
        self.settings_file = settings_file
        self.current_settings = {}
        self.init()

    def __init_config(self):
        try:
            # UserConfig init
            self.current_settings["user_cfg"] = {k: v for k, v in UserConfig.__dict__.items() if not k.startswith("_")}
            self.current_settings["user_cfg"]["ota_status"]["sys_current_version"] = DEVICE_FIRMWARE_VERSION
            self.current_settings["user_cfg"]["ota_status"]["app_current_version"] = PROJECT_VERSION

            # CloudConfig init
            self.current_settings["cloud_cfg"] = {}
            if self.current_settings["user_cfg"]["cloud"] == UserConfig._cloud.AliYun:
                if not hasattr(settings_cloud, "AliCloudConfig"):
                    raise TypeError("settings_cloud.AliCloudConfig is not exists.")
                self.current_settings["cloud_cfg"] = {k: v for k, v in settings_cloud.AliCloudConfig.__dict__.items() if not k.startswith("_")}
            elif self.current_settings["user_cfg"]["cloud"] == UserConfig._cloud.ThingsBoard:
                if not hasattr(settings_cloud, "ThingsBoardConfig"):
                    raise TypeError("ThingsBoardConfig is not exists.")
                self.current_settings["cloud_cfg"] = {k: v for k, v in settings_cloud.ThingsBoardConfig.__dict__.items() if not k.startswith("_")}

            # LocConfig init
            self.current_settings["loc_cfg"] = {k: v for k, v in LocConfig.__dict__.items() if not k.startswith("_")}
            return True
        except:
            return False

    def __read_config(self):
        if ql_fs.path_exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                self.current_settings = ujson.load(f)
                return True
        return False

    def __set_config(self, mode, key, val):
        if mode not in self.current_settings.keys():
            return False
        if mode == "user_cfg":
            if key == "phone_num":
                if not isinstance(val, str):
                    return False
                pattern = ure.compile(r"^(?:(?:\+)86)?1[3-9]\d\d\d\d\d\d\d\d\d$")
                if pattern.search(val):
                    self.current_settings[mode][key] = val
                    return True
                return False
            elif key == "loc_method":
                if not isinstance(val, int):
                    return False
                if val > UserConfig._loc_method.all:
                    return False
                self.current_settings[mode][key] = val
                return True
            elif key == "work_mode":
                if not isinstance(val, int):
                    return False
                if val > UserConfig._work_mode.intelligent:
                    return False
                self.current_settings[mode][key] = val
                return True
            elif key in ("work_cycle_period", "over_speed_threshold"):
                if not isinstance(val, int):
                    return False
                if val < 1:
                    return False
                self.current_settings[mode][key] = val
                return True
            elif key in ("low_power_alert_threshold", "low_power_shutdown_threshold"):
                if not isinstance(val, int):
                    return False
                if val < 0 or val > 100:
                    return False
                self.current_settings[mode][key] = val
                return True
            elif key in ("sw_ota", "sw_ota_auto_upgrade", "sw_voice_listen", "sw_voice_record",
                         "sw_fault_alert", "sw_low_power_alert", "sw_over_speed_alert",
                         "sw_sim_abnormal_alert", "sw_disassemble_alert", "sw_drive_behavior_alert"):
                if not isinstance(val, bool) and val not in (0, 1):
                    return False
                self.current_settings[mode][key] = bool(val)
                return True
            elif key == "ota_status":
                if not isinstance(val, dict):
                    return False
                self.current_settings[mode][key] = val
                return True
            elif key in ("user_ota_action", "drive_behavior_code", "loc_gps_read_timeout", "work_mode_timeline"):
                if not isinstance(val, int):
                    return False
                self.current_settings[mode][key] = val
                return True
        elif mode == "cloud_cfg":
            if key.lower() == "life_time":
                if not isinstance(val, int):
                    return False
                self.current_settings[mode][key] = val
                return True
            elif key.upper() in ("PK", "PS", "DK", "DS", "SERVER"):
                if not isinstance(val, str):
                    return False
                self.current_settings[mode][key] = val
                return True

        return False

    def __save_config(self):
        try:
            with open(self.settings_file, "w") as f:
                ujson.dump(self.current_settings, f)
            return True
        except:
            return False

    def __remove_config(self):
        try:
            uos.remove(self.settings_file)
            return True
        except:
            return False

    def __get_config(self):
        return self.current_settings

    @option_lock(_settings_lock)
    def init(self):
        if self.__read_config() is False:
            if self.__init_config():
                return self.__save_config()
        return False

    @option_lock(_settings_lock)
    def get(self):
        return self.__get_config()

    @option_lock(_settings_lock)
    def set(self, mode, key, val):
        return self.__set_config(mode, key, val)

    @option_lock(_settings_lock)
    def save(self):
        return self.__save_config()

    @option_lock(_settings_lock)
    def remove(self):
        return self.__remove_config()

    @option_lock(_settings_lock)
    def reset(self):
        if self.__remove_config():
            if self.__init_config():
                return self.__save_config()
        return False
