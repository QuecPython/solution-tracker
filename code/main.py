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

from usr.tracker import Tracker
from usr.settings import settings
from usr.settings import default_values_sys
from usr.settings import PROJECT_NAME
from usr.settings import PROJECT_VERSION
from usr.logging import getLogger

log = getLogger(__name__)


def main():
    log.info('PROJECT_NAME: %s' % PROJECT_NAME)
    log.info('PROJECT_VERSION: %s' % PROJECT_VERSION)
    current_settings = settings.get()

    tracker = Tracker()
    # Start Device Check
    tracker.device_check()

    # Start OTA Check
    if current_settings['sys']['cloud'] == default_values_sys._cloud.quecIot and \
            current_settings['app']['sw_ota'] is True:
        tracker.remote.check_ota()

    # Start PowerManage
    # Init Low Energy Work Mode
    tracker.power_manage.low_energy_init()
    # Start RTC
    tracker.power_manage.start_rtc()


if __name__ == '__main__':
    main()
