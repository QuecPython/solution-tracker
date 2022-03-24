import uos
import utime
import ql_fs
import ujson
import _thread
import sys_bus

from queue import Queue

import usr.settings as settings

from usr.common import Singleton
from usr.logging import getLogger
from usr.settings import DATA_NON_LOCA
from usr.settings import DATA_LOCA_NON_GPS
from usr.settings import DATA_LOCA_GPS

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
            if action is False:
                self.tracker.remote.cloud_ota_action(0)
            elif action is True:
                self.tracker.remote.cloud_ota_action(1)

    def ota_status(self, perm, status=None):
        if perm == 'r':
            self.tracker.device_data_report()
        elif perm == 'w':
            if status is not None:
                settings.settings.set('ota_status', status)
                settings.settings.save()


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
                set_res = settings.settings.set(arg[0], arg[1])
                log.debug('key: %s, val: %s, set_res: %s', (arg[0], arg[1], set_res))
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
            self.tracker.remote.cloud_ota_action()


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
        args = data[1]
        if hasattr(DownLinkOptionObj, option_attr):
            option_fun = getattr(DownLinkOptionObj, option_attr)
            option_fun(*args)
            if self.remote_read_cb:
                self.remote_read_cb(*data)
            else:
                log.warn('Remote read callback is not defined.')
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
            if self.tracker.net_enable is False:
                raise RemoteError('Net Is Disconnected.')
            for key, value in hist.items():
                # Check if non_loca data (sensor or device info data) or location gps data or location non-gps data (cell/wifi-locator data)
                if key == 'hist_data':
                    for i, data in enumerate(value):
                        ntry = 0
                        # Try at most 3 times to post data to server.
                        while not self.cloud.post_data(data):
                            ntry += 1
                            if ntry >= 3:  # Data post failed after 3 times, maybe network error?
                                raise RemoteError('Data post failed.')  # Stop posting more data, go to exception handler.
                            utime.sleep(1)
                        else:
                            value.pop(i)         # Pop data from data-list after posting sueecss.
                            need_refresh = True  # Data in hist-dictionary changed, need to refresh history file.
        except Exception:
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
                if self.tracker.net_enable is True:
                    if self.cloud.post_data(data[1]):
                        sys_bus.publish(data[0], 'true')
                        continue
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
            self.cloud = QuecThing(cloud_init_params['PK'], cloud_init_params['PS'], cloud_init_params['DK'], cloud_init_params['DS'], self.downlink_queue)
        elif current_settings['sys']['cloud'] == settings.default_values_sys._cloud.AliYun:
            self.cloud = AliYunIot(cloud_init_params['PK'], cloud_init_params['PS'], cloud_init_params['DK'], cloud_init_params['DS'], self.downlink_queue)
        else:
            raise settings.SettingsError('Current cloud (0x%X) not supported!' % current_settings['sys']['cloud'])

        _thread.start_new_thread(downlink_process, (self,))
        _thread.start_new_thread(uplink_process, (self,))

    def read_history(self):
        '''
        {
            "non_loca": [
                {
                    'switch': True,
                    'energy': 100
                },
                {
                    'switch': True,
                    'energy': 100
                }
            ],

            "loca_non_gps": [
                (117.1138, 31.82279, 550),
                (117.1138, 31.82279, 550)
            ],

            "loca_gps": [
                ['$GPRMCx,x,x,x', '$GPGGAx,x,x,x'],
                ['$GPRMCx,x,x,x', '$GPGGAx,x,x,x']
            ]
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
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
            if current_settings['app']['sw_ota'] is True:
                self.cloud.dev_info_report()
            else:
                raise settings.SettingsError('OTA upgrade is disabled!')
        else:
            raise settings.SettingsError('Current cloud (0x%X) not supported!' % current_settings['sys']['cloud'])

    def cloud_ota_action(self, val=1):
        current_settings = settings.settings.get()
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
            self.cloud.ota_action(val)
            if val == 0:
                settings.settings.set('ota_status', 0)
                settings.settings.save()
        else:
            raise settings.SettingsError('Current cloud (0x%X) not supported!' % current_settings['sys']['cloud'])
