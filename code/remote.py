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
import ql_fs
import ujson
import _thread
import sys_bus

from queue import Queue

import usr.settings as settings

from usr.ota import OTA
from usr.common import Singleton
from usr.logging import getLogger
from usr.settings import DATA_NON_LOCA
from usr.settings import DATA_LOCA_GPS
from usr.settings import DATA_LOCA_NON_GPS
from usr.settings import SYSNAME
from usr.settings import PROJECT_NAME

if settings.settings.get()['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
    from usr.quecthing import QuecThing
if settings.settings.get()['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
    from usr.aliyunIot import AliYunIot

log = getLogger(__name__)


class RemoteError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ControllerError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Controller(Singleton):
    def __init__(self, tracker):
        self.tracker = tracker

    def power_switch(self, perm, flag=None):
        if perm == 'r':
            self.tracker.device_data_report()
        elif perm == 'w':
            if flag is True:
                self.tracker.device_data_report()
            elif flag is False:
                self.tracker.device_data_report(power_switch=False, msg='power_down')
        else:
            raise ControllerError('Controller switch permission error %s.' % perm)

    def energy(self, perm):
        if perm == 'r':
            self.tracker.device_data_report()
        else:
            raise ControllerError('Controller energy permission error %s.' % perm)

    def user_ota_action(self, perm, action):
        if perm == 'w':
            if action == 0:
                self.tracker.remote.cloud_ota_action(0)
            elif action == 1:
                self.tracker.remote.cloud_ota_action(1)

    def ota_status(self, perm, upgrade_info=None):
        if perm == 'r':
            self.tracker.device_data_report()
        elif perm == 'w':
            if upgrade_info:
                current_settings = settings.settings.get()
                ota_status_info = current_settings['sys']['ota_status']
                if ota_status_info['sys_target_version'] == '--' and ota_status_info['app_target_version'] == '--':
                    ota_info = {}
                    if upgrade_info[0] == settings.SYSNAME:
                        ota_info['upgrade_module'] = 1
                        ota_info['sys_target_version'] = upgrade_info[2]
                    elif upgrade_info[0] == settings.PROJECT_NAME:
                        ota_info['upgrade_module'] = 2
                        ota_info['app_target_version'] = upgrade_info[2]
                    ota_info['upgrade_status'] = upgrade_info[1]
                    ota_status_info.update(ota_info)
                    settings.settings.set('ota_status', ota_status_info)
                    settings.settings.save()

    def power_restart(self, perm, flag):
        if perm == 'w':
            self.tracker.device_data_report(power_switch=False, msg='power_restart')

    def work_cycle_period(self, perm, period):
        if perm == 'w':
            self.tracker.power_manage.rtc.enable_alarm(0)
            self.tracker.power_manage.start_rtc()


class DownLinkOption(object):
    def __init__(self, tracker):
        self.tracker = tracker
        self.controller = Controller(self.tracker)

    def raw_data(self, *args, **kwargs):
        pass

    def object_model(self, *args, **kwargs):
        setting_flag = 0

        for arg in args:
            if hasattr(settings.default_values_app, arg[0]):
                key = arg[0]
                value = arg[1]
                if key == 'loc_method':
                    v = '0b'
                    v += str(int(value.get(3, 0)))
                    v += str(int(value.get(2, 0)))
                    v += str(int(value.get(1, 0)))
                    value = int(v, 2)
                set_res = settings.settings.set(key, value)
                log.debug('key: %s, val: %s, set_res: %s' % (key, value, set_res))
                if setting_flag == 0:
                    setting_flag = 1
            if hasattr(self.controller, arg[0]):
                getattr(self.controller, arg[0])(*('w', arg[1]))

        if setting_flag:
            settings.settings.save()

    def query(self, *args, **kwargs):
        self.tracker.device_data_report()
        # for arg in args:
        #     if hasattr(settings.default_values_app, arg):
        #         current_settings = settings.settings.get()
        #         self.tracker.remote.post_data({arg: current_settings.get('app', {}).get(arg)})
        #     elif hasattr(self.controller, arg):
        #         getattr(self.controller, arg)(*('r'))
        #     else:
        #         pass

    def ota_plain(self, *args, **kwargs):
        current_settings = settings.settings.get()
        if current_settings['app']['sw_ota'] and current_settings['app']['sw_ota_auto_upgrade']:
            if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
                self.tracker.remote.cloud_ota_action(val=1)
            elif current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
                log.debug('ota_plain args: %s' % str(args))
                log.debug('ota_plain kwargs: %s' % str(kwargs))
                self.tracker.remote.cloud_ota_action(val=1, kwargs=kwargs)

    def ota_file_download(self, *args, **kwargs):
        log.debug('ota_file_download: %s' % str(args))


def downlink_process(argv):
    self = argv
    while True:
        '''
        Recv data from quecIot or AliYun or other server.
        Data format should be unified at the process module file of its own before put to downlink_queue.

        Data format:
        ('object_model', [('phone_num', '123456789'),...])
        ('query', ['phone_num',...])
        '''
        data = self.downlink_queue.get()

        DownLinkOptionObj = DownLinkOption(tracker=self.tracker)
        option_attr = data[0]
        args = data[1] if not isinstance(data[1], dict) else ()
        kwargs = data[1] if isinstance(data[1], dict) else {}
        if hasattr(DownLinkOptionObj, option_attr):
            option_fun = getattr(DownLinkOptionObj, option_attr)
            option_fun(*args, **kwargs)
            if self.remote_read_cb:
                self.remote_read_cb(*data)
        else:
            # TODO: Raise Error OR Conntinue
            raise RemoteError('DownLinkOption has no accribute %s.' % option_attr)


def uplink_process(argv):
    self = argv
    while True:

        '''
        We need to post data in tracker_data.hist file to server firstly every time.
        If still can't post all data to server, stop posting, but to append all data in uplink_queue to tracker_data.hist.
        When data in tracker_data.hist and in uplink_queue is processed, wait for new data coming into uplink_queue.
        If get new data, try to post data again, if fail, add data to tracker_data.hist file.
        Otherwise, keep waiting untill new data coming, then process could go to the start of loopwhile, and data in tracker_data.hist could be processed again.
        '''

        need_refresh = False

        # Read history data that didn't send to server intime to hist-dictionary.
        hist = self.read_history()
        try:
            if self.cloud_connect() is False:
                raise RemoteError('Net Is Disconnected.')
            for key, value in hist.items():
                # Check if non_loca data (sensor or device info data) or location gps data or location non-gps data (cell/wifi-locator data)
                if key == 'hist_data':
                    for i, data in enumerate(value):
                        if not self.cloud.post_data(data):
                            self.cloud.cloud_init(enforce=True)
                            if not self.cloud.post_data(data):
                                raise RemoteError('Data post failed.')  # Stop posting more data, go to exception handler.
                                break
                        value.pop(i)
                        need_refresh = True  # Data in hist-dictionary changed, need to refresh history file.
        except Exception as e:
            log.error('uplink_process Error: %s' % e)
            while True:  # Put all data in uplink_queue to hist-dictionary.
                if self.uplink_queue.size():
                    data = self.uplink_queue.get()
                    if data:
                        if data[1]:
                            if hist.get('hist_data') is None:
                                hist['hist_data'] = []
                            hist['hist_data'].append(data[1])
                            need_refresh = True
                        sys_bus.publish(data[0], 'false')
                else:
                    break
        finally:
            if need_refresh:
                # Flush data in hist-dictionary to tracker_data.hist file.
                self.refresh_history(hist)

        # When comes to this, wait for new data coming into uplink_queue.
        data = self.uplink_queue.get()
        if data:
            if data[1]:
                if self.cloud_connect() is True:
                    if self.cloud.post_data(data[1]):
                        sys_bus.publish(data[0], 'true')
                        continue
                    else:
                        self.cloud.cloud_init(enforce=True)
                        if self.cloud.post_data(data[1]):
                            sys_bus.publish(data[0], 'true')
                            continue
                else:
                    log.warn('Net Is Disconnected.')
                self.add_history(data[1])
            sys_bus.publish(data[0], 'false')


class Remote(Singleton):
    _history = '/usr/tracker_data.hist'

    def __init__(self, tracker, remote_read_cb=None):
        self.tracker = tracker
        self.remote_read_cb = remote_read_cb
        self.downlink_queue = Queue(maxsize=64)
        self.uplink_queue = Queue(maxsize=64)

        self.DATA_NON_LOCA = DATA_NON_LOCA
        self.DATA_LOCA_NON_GPS = DATA_LOCA_NON_GPS
        self.DATA_LOCA_GPS = DATA_LOCA_GPS

        current_settings = settings.settings.get()
        cloud_init_params = current_settings['sys']['cloud_init_params']
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
            self.cloud = QuecThing(
                cloud_init_params['PK'],
                cloud_init_params['PS'],
                cloud_init_params['DK'],
                cloud_init_params['DS'],
                cloud_init_params['SERVER'],
                self.downlink_queue
            )
        elif current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
            self.cloud = AliYunIot(
                cloud_init_params['PK'],
                cloud_init_params['PS'],
                cloud_init_params['DK'],
                cloud_init_params['DS'],
                cloud_init_params['SERVER'],
                self.downlink_queue
            )
        else:
            raise settings.SettingsError('Current cloud (0x%X) not supported!' % current_settings['sys']['cloud'])

        _thread.start_new_thread(downlink_process, (self,))
        _thread.start_new_thread(uplink_process, (self,))

    def read_history(self):
        '''
        {
            "hist_data": [
                {
                    'switch': True,
                    'energy': 100
                },
                {
                    'switch': True,
                    'energy': 100
                },
                'gps': ['$GPRMCx,x,x,x', '$GPGGAx,x,x,x'],
                'non_gps': ['LBS'],
            ],
        }
        '''
        if ql_fs.path_exists(self._history):
            with open(self._history, 'r') as f:
                try:
                    res = ujson.load(f)
                    if isinstance(res, dict):
                        return res
                    return {}
                except Exception:
                    return {}
        else:
            return {}

    def add_history(self, data):
        try:
            with open(self._history, 'r') as f:
                res = ujson.load(f)
        except Exception:
            res = {}

        if not isinstance(res, dict):
            res = {}

        if res.get('hist_data') is None:
            res['hist_data'] = []

        res['hist_data'].append(data)

        return self.refresh_history(res)

    def refresh_history(self, hist_dict):
        try:
            with open(self._history, 'w') as f:
                ujson.dump(hist_dict, f)
                return True
        except Exception:
            return False

    def clean_history(self):
        uos.remove(self._history)

    def cloud_connect(self):
        net_check_res = self.tracker.check.net_check()
        if net_check_res == (3, 1):
            return self.cloud.cloud_init()
        else:
            return False

    def post_data(self, topic, data):
        '''
        Data format to post:

        {
            'switch': True,
            'energy': 100,
            'non_gps': [],
            'gps': []
        }
        '''
        self.uplink_queue.put((topic, data))

    def check_ota(self):
        current_settings = settings.settings.get()
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot or \
                current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
            if current_settings['app']['sw_ota'] is True:
                log.debug('OTA Check To Report Dev Info.')
                self.cloud.ota_request()
            else:
                log.warn('OTA Upgrade Is Disabled!')
        else:
            log.error('Current Cloud (0x%X) Not Supported!' % current_settings['sys']['cloud'])

    def cloud_ota_action(self, val=1, kwargs=None):
        current_settings = settings.settings.get()
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
            self.cloud.ota_action(val)
            if val == 0:
                self.tracker.ota_params_reset()
        else:
            if val == 0:
                current_settings = settings.settings.get()
                ota_status_info = current_settings['sys']['ota_status']
                upgrade_module = SYSNAME if ota_status_info['upgrade_module'] == 1 else PROJECT_NAME
                self.cloud.ota_device_progress(step=-1, desc='User cancels upgrade.', module=upgrade_module)
                self.tracker.ota_params_reset()
            else:
                upgrade_module = kwargs.get('module', '')
                file_info = [{'size': i['fileSize'], 'url': i['fileUrl'], 'md5': i['fileMd5']} for i in kwargs.get('files', [])]
                if not file_info:
                    file_info = [{'size': kwargs['size'], 'url': kwargs['url'], 'md5': kwargs['md5']}]
                ota_obj = OTA(upgrade_module, file_info)
                ota_obj.start()
                self.downlink_queue.put(('object_model', [('power_restart', 1)]))
