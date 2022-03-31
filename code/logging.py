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
from usr.settings import settings

current_settings = settings.get()


def asyncLog(name, level, *message, timeout=None, await_connection=True):
        '''
        pass
        #
        # yield config.getMQTT().publish(base_topic.format(level), message, qos=1, timeout=timeout,
        #                                await_connection=await_connection)
        '''
        pass


def log(name, level, *message, local_only=False, return_only=False, timeout=None):
    if not current_settings.get('sys', {}).get('sw_log', True):
        return

    if hasattr(utime, "strftime"):
        print("[{}]".format(utime.strftime("%Y-%m-%d %H:%M:%S")), "[{}]".format(name),
              "[{}]".format(level), *message)
    else:
        t = utime.localtime()
        print("[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]".format(*t), "[{}]".format(name),
              "[{}]".format(level), *message)
    if return_only:
        return
    if not local_only:
        pass


class Logger:
    def __init__(self, name):
        self.name = name

    def critical(self, *message, local_only=True):
        log(self.name, "critical", *message, local_only=local_only, timeout=None)

    def error(self, *message, local_only=True):
        log(self.name, "error", *message, local_only=local_only, timeout=None)

    def warn(self, *message, local_only=True):
        log(self.name, "warn", *message, local_only=local_only, timeout=None)

    def info(self, *message, local_only=True):
        log(self.name, "info", *message, local_only=local_only, timeout=20)

    def debug(self, *message, local_only=True):
        log(self.name, "debug", *message, local_only=local_only, timeout=5)

    def asyncLog(self, level, *message, timeout=True):
        log(self.name, level, *message, return_only=True)
        if timeout == 0:
            return
        asyncLog(self.name, level, *message, timeout=timeout)


def getLogger(name):
    return Logger(name)
