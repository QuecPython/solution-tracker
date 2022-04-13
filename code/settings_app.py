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


class default_values_app(object):
    """
    App default settings
    """

    class _loc_method(object):
        none = 0x0
        gps = 0x1
        cell = 0x2
        wifi = 0x4
        all = 0x7

    class _work_mode(object):
        cycle = 0x1
        intelligent = 0x2

    class _drive_behavior(object):
        suddenly_start = 0x0
        suddenly_stop = 0x1
        suddenly_turn_left = 0x2
        suddenly_turn_right = 0x3

    """
    variables of App default settings below MUST NOT start with "_"
    """

    phone_num = ""

    loc_method = _loc_method.gps

    work_mode = _work_mode.cycle

    work_cycle_period = 30

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
