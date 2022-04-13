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
import _thread

from queue import Queue
from machine import RTC

from usr.common import Observable
from usr.logging import getLogger

log = getLogger(__name__)

LOW_ENERGY_METHOD = ("NULL", "PM", "PSM", "POWERDOWN")


class LowEnergyRTC(Observable):

    def __init__(self):
        super().__init__()

        self.__period = 60
        self.__low_energy_method = "PM"
        self.__thread_id = None

        self.__lpm_fd = None
        self.__pm_lock_name = "low_energy_pm_lock"
        self.__low_energy_queue = Queue(maxsize=8)

        self.__rtc = RTC()
        self.__rtc.register_callback(self.__rtc_callback)

    def __rtc_callback(self, args):
        self.enable_rtc(0)
        self.__low_energy_queue.put(self.__low_energy_method)

    def __low_energy_work(self, lowenergy_tag):
        while True:
            data = self.__low_energy_queue.get()
            log.debug("__low_energy_work data: %s, lowenergy_tag: %s" % (data, lowenergy_tag))
            if data:
                if lowenergy_tag:
                    if self.__lpm_fd is None:
                        self.__lpm_fd = pm.create_wakelock(self.__pm_lock_name, len(self.__pm_lock_name))
                        pm.autosleep(1)
                    wlk_res = pm.wakelock_lock(self.__lpm_fd)
                    log.debug("pm.wakelock_lock %s." % ("Success" if wlk_res == 0 else "Falied"))

                self.notifyObservers(self, *(data,))

                if lowenergy_tag:
                    wulk_res = pm.wakelock_unlock(self.__lpm_fd)
                    log.debug("pm.wakelock_unlock %s." % ("Success" if wulk_res == 0 else "Falied"))

    def get_period(self):
        return self.__period

    def set_period(self, seconds=0):
        if isinstance(seconds, int) and seconds > 0:
            self.__period = seconds
            return True
        return False

    def get_low_energy_method(self):
        return self.__low_energy_method

    def set_low_energy_method(self, method):
        if method in LOW_ENERGY_METHOD:
            self.__low_energy_method = method
            return True
        return False

    def get_lpm_fd(self):
        return self.__lpm_fd

    def low_energy_init(self):
        try:
            if self.__thread_id is not None:
                _thread.stop_thread(self.__thread_id)
            if self.__lpm_fd is not None:
                pm.delete_wakelock(self.__lpm_fd)
                self.__lpm_fd = None

            if self.__low_energy_method == "PM":
                self.__thread_id = _thread.start_new_thread(self.__low_energy_work, (True,))
                self.__lpm_fd = pm.create_wakelock(self.__pm_lock_name, len(self.__pm_lock_name))
                pm.autosleep(1)
            elif self.__low_energy_method == "NULL":
                self.__thread_id = _thread.start_new_thread(self.__low_energy_work, (False,))
            elif self.__low_energy_method in ("PSM", "POWERDOWN"):
                pass
            return True
        except:
            return False

    def start_rtc(self):
        atime = utime.localtime(utime.mktime(utime.localtime()) + self.__period)
        alarm_time = [atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0]
        if self.__rtc.set_alarm(alarm_time) == 0:
            return self.enable_rtc(1)
        return False

    def enable_rtc(self, enable):
        enable_alarm_res = self.__rtc.enable_alarm(enable)
        return True if enable_alarm_res == 0 else False
