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

from usr.settings_loc import LocConfig


class UserConfig(object):

    class _work_mode(object):
        cycle = 0x1
        intelligent = 0x2

    class _drive_behavior_code(object):
        none = 0x0
        sharply_start = 0x1
        sharply_stop = 0x2
        sharply_turn_left = 0x3
        sharply_turn_right = 0x4

    class _ota_upgrade_status(object):
        none = 0x0
        to_be_updated = 0x1
        updating = 0x2
        update_successed = 0x3
        update_failed = 0x4

    class _ota_upgrade_module(object):
        none = 0x0
        sys = 0x1
        app = 0x2

    phone_num = ""

    low_power_alert_threshold = 20

    low_power_shutdown_threshold = 5

    over_speed_threshold = 50

    sw_ota = True

    sw_ota_auto_upgrade = True

    sw_voice_listen = False

    sw_voice_record = False

    sw_fault_alert = True

    sw_low_power_alert = True

    sw_over_speed_alert = True

    sw_sim_abnormal_alert = True

    sw_disassemble_alert = True

    sw_drive_behavior_alert = True

    drive_behavior_code = _drive_behavior_code.none

    loc_method = LocConfig._loc_method.all

    loc_gps_read_timeout = 300

    work_mode = _work_mode.cycle

    work_mode_timeline = 3600

    work_cycle_period = 30

    user_ota_action = -1

    ota_status = {
        "sys_current_version": "",
        "sys_target_version": "--",
        "app_current_version": "",
        "app_target_version": "--",
        "upgrade_module": _ota_upgrade_module.none,
        "upgrade_status": _ota_upgrade_status.none,
    }
