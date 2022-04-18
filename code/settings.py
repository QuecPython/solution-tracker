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

from usr.modules.common import Singleton
from usr.modules.common import option_lock
from usr.settings_sys import SYSConfig
from usr.settings_loc import LocConfig
from usr.settings_alicloud import AliCloudConfig
from usr.settings_queccloud import QuecCloudConfig
from usr.settings_jtt808 import JTT808Config
from usr.settings_user import UserConfig


PROJECT_NAME = "QuecPython-Tracker"

PROJECT_VERSION = "2.1.0"

DEVICE_FIRMWARE_NAME = uos.uname()[0].split("=")[1]

DEVICE_FIRMWARE_VERSION = modem.getDevFwVersion()


_settings_lock = _thread.allocate_lock()


class Settings(Singleton):

    def __init__(self, settings_file="/usr/tracker_settings.json"):
        self.settings_file = settings_file
        self.current_settings = {}
        self.init()

    @option_lock(_settings_lock)
    def init(self):
        try:
            if ql_fs.path_exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    self.current_settings = ujson.load(f)
                return True

            # SYSConfig init
            self.current_settings["sys"] = {k: v for k, v in SYSConfig.__dict__.items() if not k.startswith("_")}

            # CloudConfig init
            if self.current_settings["sys"]["cloud"] == SYSConfig._cloud.AliYun:
                self.current_settings["cloud"] = {k: v for k, v in AliCloudConfig.__dict__.items() if not k.startswith("_")}
            elif self.current_settings["sys"]["cloud"] == SYSConfig._cloud.quecIot:
                self.current_settings["cloud"] = {k: v for k, v in QuecCloudConfig.__dict__.items() if not k.startswith("_")}
            elif self.current_settings["sys"]["cloud"] == SYSConfig._cloud.JTT808:
                self.current_settings["cloud"] = {k: v for k, v in JTT808Config.__dict__.items() if not k.startswith("_")}
            elif self.current_settings["sys"]["cloud"] == SYSConfig._cloud.customization:
                self.current_settings["cloud"] = {}
            else:
                self.current_settings["cloud"] = {}

            # LocConfig init
            if self.current_settings["sys"]["base_cfg"]["LocConfig"]:
                self.current_settings["LocConfig"] = {k: v for k, v in LocConfig.__dict__.items() if not k.startswith("_")}

            # UserConfig init
            if self.current_settings["sys"]["user_cfg"]:
                self.current_settings["user_cfg"] = {k: v for k, v in UserConfig.__dict__.items() if not k.startswith("_")}
                self.current_settings["user_cfg"]["ota_status"]["sys_current_version"] = DEVICE_FIRMWARE_VERSION
                self.current_settings["user_cfg"]["ota_status"]["app_current_version"] = PROJECT_VERSION

            with open(self.settings_file, "w") as f:
                ujson.dump(self.current_settings, f)

            return True
        except:
            return False

    @option_lock(_settings_lock)
    def get(self):
        return self.current_settings

    @option_lock(_settings_lock)
    def set(self, opt, val):
        if opt in self.current_settings["user_cfg"]:
            if opt == "phone_num":
                if not isinstance(val, str):
                    return False
                pattern = ure.compile(r"^(?:(?:\+)86)?1[3-9]\d\d\d\d\d\d\d\d\d$")
                if pattern.search(val):
                    self.current_settings["user_cfg"][opt] = val
                    return True
                return False
            elif opt == "loc_method":
                if not isinstance(val, int):
                    return False
                if val > LocConfig._loc_method.all:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt == "work_mode":
                if not isinstance(val, int):
                    return False
                if val > UserConfig._work_mode.intelligent:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("work_cycle_period", "over_speed_threshold"):
                if not isinstance(val, int):
                    return False
                if val < 1:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("low_power_alert_threshold", "low_power_shutdown_threshold"):
                if not isinstance(val, int):
                    return False
                if val < 0 or val > 100:
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("sw_ota", "sw_ota_auto_upgrade", "sw_voice_listen", "sw_voice_record",
                         "sw_fault_alert", "sw_low_power_alert", "sw_over_speed_alert",
                         "sw_sim_abnormal_alert", "sw_disassemble_alert", "sw_drive_behavior_alert"):
                if not isinstance(val, bool):
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt == "ota_status":
                if not isinstance(val, dict):
                    return False
                self.current_settings["user_cfg"][opt] = val
                return True
            elif opt in ("user_ota_action", "drive_behavior_code"):
                if not isinstance(val, int):
                    return False
                self.current_settings["sys"][opt] = val
                return True
        elif opt == "cloud":
            if not isinstance(val, dict):
                return False
            self.current_settings[opt] = val
            return True

        return False

    @option_lock(_settings_lock)
    def save(self):
        try:
            with open(self.settings_file, "w") as f:
                ujson.dump(self.current_settings, f)
            return True
        except:
            return False

    @option_lock(_settings_lock)
    def reset(self):
        try:
            uos.remove(self.settings_file)
            return True
        except:
            return False


settings = Settings()
