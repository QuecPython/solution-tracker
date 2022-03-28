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

import pm
import utime
import modem
import _thread

from queue import Queue
from machine import RTC

from usr.common import Singleton
from usr.logging import getLogger
from usr.settings import settings
from usr.settings import LOWENERGYMAP
from usr.settings import default_values_app

log = getLogger(__name__)


class PowerManage(Singleton):

    def __init__(self, tracker, callback=None):
        self.tracker = tracker
        self.callback = callback

        self.lpm_fd = None
        self.low_energy_queue = Queue(maxsize=8)

        self.period = None
        self.low_energy_method = None
        self.set_period()
        self.get_low_energy_method()

        self.rtc = RTC()
        self.rtc.register_callback(self.rtc_callback)

    def set_period(self, seconds=None):
        if seconds is None:
            current_settings = settings.get()
            seconds = current_settings['app']['work_cycle_period']
        self.period = seconds

    def start_rtc(self):
        current_settings = settings.get()
        if current_settings['app']['work_mode'] == default_values_app._work_mode.intelligent:
            if self.tracker.locator.gps:
                gps_data = self.tracker.locator.gps.read()
                speed = self.tracker.locator.gps.read_location_GxVTG_speed(gps_data)
                if not speed:
                    return
                elif float(speed) <= 0:
                    return

        self.set_period()
        atime = utime.localtime(utime.mktime(utime.localtime()) + self.period)
        alarm_time = [atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0]
        self.rtc.set_alarm(alarm_time)
        self.rtc.enable_alarm(1)

    def rtc_callback(self, args):
        self.rtc.enable_alarm(0)
        if self.low_energy_method == 'PM':
            self.low_energy_queue.put('wakelock_unlock')
        elif self.low_energy_method == 'PSM':
            self.low_energy_queue.put('psm')
        elif self.low_energy_method == 'POWERDOWN':
            self.low_energy_queue.put('power_dwon')
        elif self.low_energy_method is None:
            self.low_energy_queue.put('cycle_report')

    def get_low_energy_method(self):
        current_settings = settings.get()
        device_model = modem.getDevModel()
        support_methds = LOWENERGYMAP.get(device_model, [])
        if support_methds:
            if self.period >= current_settings['sys']['work_mode_timeline']:
                if "PSM" in support_methds:
                    self.low_energy_method = "PSM"
                elif "POWERDOWN" in support_methds:
                    self.low_energy_method = "POWERDOWN"
                elif "PM" in support_methds:
                    self.low_energy_method = "PM"
            else:
                if "PM" in support_methds:
                    self.low_energy_method = "PM"

        return self.low_energy_method

    def low_energy_init(self):
        if self.low_energy_method == 'PM':
            _thread.start_new_thread(self.low_energy_work, (True,))
            self.lpm_fd = pm.create_wakelock("lowenergy_lock", len("lowenergy_lock"))
            pm.autosleep(1)
        elif self.low_energy_method == 'PSM':
            pass
        elif self.low_energy_method == 'POWERDOWN':
            pass
        elif self.low_energy_method is None:
            _thread.start_new_thread(self.low_energy_work, (False,))

    def low_energy_work(self, lowenergy_tag):
        while True:
            data = self.low_energy_queue.get()
            if data:
                if lowenergy_tag:
                    if self.lpm_fd is None:
                        self.lpm_fd = pm.create_wakelock("lowenergy_lock", len("lowenergy_lock"))
                        pm.autosleep(1)
                    pm.wakelock_lock(self.lpm_fd)

                over_speed_check_res = self.tracker.get_over_speed_check()
                self.tracker.device_data_report(event_data=over_speed_check_res, msg=data)
