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
import _thread

from usr.common import Singleton
from usr.settings_app import default_values_app
from usr.settings_sys import default_values_sys

# For Other Module To Import
from usr.settings_sys import SYSNAME, PROJECT_NAME, PROJECT_VERSION, DEVICE_FIRMWARE_VERSION, \
    DATA_NON_LOCA, DATA_LOCA_NON_GPS, DATA_LOCA_GPS, ALERTCODE, LOWENERGYMAP

SYSNAME
PROJECT_NAME
PROJECT_VERSION
DEVICE_FIRMWARE_VERSION
DATA_NON_LOCA
DATA_LOCA_NON_GPS
DATA_LOCA_GPS
ALERTCODE
LOWENERGYMAP

tracker_settings_file = '/usr/tracker_settings.json'

_settings_lock = _thread.allocate_lock()


def settings_lock(func_name):
    def settings_lock_fun(func):
        def wrapperd_fun(*args, **kwargs):
            with _settings_lock:
                return func(*args, **kwargs)
        return wrapperd_fun
    return settings_lock_fun


class SettingsError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Settings(Singleton):

    def __init__(self):
        self.current_settings = {}
        self.current_settings_app = {}
        self.current_settings_sys = {}
        self.init()

    @settings_lock('Settings.init')
    def init(self):
        try:
            default_values_sys.locator_init_params = default_values_sys._get_locator_init_params(default_values_app.loc_method)
            default_values_sys.cloud_init_params = default_values_sys._get_cloud_init_params(default_values_sys.cloud)
            default_values_sys.ota_status = default_values_sys._ota_status_init_params()

            default_settings_app = {k: v for k, v in default_values_app.__dict__.items() if not k.startswith('_')}
            default_settings_sys = {k: v for k, v in default_values_sys.__dict__.items() if not k.startswith('_')}
            default_settings = {'app': default_settings_app, 'sys': default_settings_sys}

            if not ql_fs.path_exists(tracker_settings_file):
                with open(tracker_settings_file, 'w') as f:
                    ujson.dump(default_settings, f)
                self.current_settings = dict(default_settings)
            else:
                with open(tracker_settings_file, 'r') as f:
                    self.current_settings = ujson.load(f)
            return True
        except:
            return False

    @settings_lock('Settings.get')
    def get(self):
        return self.current_settings

    @settings_lock('Settings.set')
    def set(self, opt, val):
        if opt in self.current_settings['app']:
            if opt == 'phone_num':
                if not isinstance(val, str):
                    return False
                pattern = ure.compile(r'^(?:(?:\+)86)?1[3-9]\d\d\d\d\d\d\d\d\d$')
                if pattern.search(val):
                    self.current_settings['app'][opt] = val
                    return True
                return False

            elif opt == 'loc_method':
                if not isinstance(val, int):
                    return False
                if val > default_values_app._loc_method.all:
                    return False
                self.current_settings['app'][opt] = val
                self.current_settings['sys']['locator_init_params'] = default_values_sys._get_locator_init_params(val)
                return True

            elif opt == 'work_mode':
                if not isinstance(val, int):
                    return False
                if val > default_values_app._work_mode.intelligent:
                    return False
                self.current_settings['app'][opt] = val
                return True

            elif opt == 'work_cycle_period':
                if not isinstance(val, int):
                    return False
                if val < 1:
                    return False
                self.current_settings['app'][opt] = val
                return True

            elif opt == 'low_power_alert_threshold' or opt == 'low_power_shutdown_threshold':
                if not isinstance(val, int):
                    return False
                if val < 0 or val > 100:
                    return False
                self.current_settings['app'][opt] = val
                return True

            elif opt in (
                    'sw_ota', 'sw_ota_auto_upgrade', 'sw_voice_listen', 'sw_voice_record',
                    'sw_fault_alert', 'sw_low_power_alert', 'sw_over_speed_alert',
                    'sw_sim_abnormal_alert', 'sw_disassemble_alert', 'sw_drive_behavior_alert'):
                if not isinstance(val, bool):
                    return False
                self.current_settings['app'][opt] = val
                return True
            elif opt == 'over_speed_threshold':
                if not isinstance(val, int):
                    return False
                if val < 1:
                    return False
                self.current_settings['app'][opt] = val
                return True
            else:
                return False
        if opt in self.current_settings['sys']:
            if opt == 'sw_log':
                if not isinstance(val, bool):
                    return False
                self.current_settings['sys'][opt] = val
                return True
            elif opt == 'ota_status':
                if not isinstance(val, dict):
                    return False
                self.current_settings['sys'][opt] = val
                return True
            elif opt == 'cloud_init_params':
                if not isinstance(val, dict):
                    return False
                self.current_settings['sys'][opt] = val
                return True
        else:
            return False

    @settings_lock('Settings.save')
    def save(self):
        try:
            with open(tracker_settings_file, 'w') as f:
                ujson.dump(self.current_settings, f)
            return True
        except:
            return False

    @settings_lock('Settings.reset')
    def reset(self):
        try:
            uos.remove(tracker_settings_file)
            return True
        except:
            return False


settings = Settings()
