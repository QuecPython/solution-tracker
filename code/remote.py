
import utime
import ql_fs
import ujson
import uos
import _thread
from queue import Queue
import usr.settings as settings
import usr.dev_info as dev_info
from usr.logging import getLogger

log = getLogger(__name__)

current_settings = settings.current_settings

if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
    from usr.quecthing import QuecThing
    from usr.quecthing import DATA_NON_LOCA, DATA_LOCA_NON_GPS, DATA_LOCA_GPS


class RemoteError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class DownLinkOption(object):
    def __init__(self, remote_obj):
        self.remote_obj = remote_obj

    def remote_post_data(self, key, val):
        # TODO: Self funtion over to post or not.
        self.remote_obj.post_data(self.remote_obj.DATA_NON_LOCA, {key: val})

    def get_switch(self, *args):
        return True

    def set_switch(self, *args):
        if args[0] is False:
            # TODO: How to checkout msg that is posted over before power down.
            pass
        else:
            return True

    def get_energy(self, *args):
        # TODO: How to get energy from Power.getVbatt().
        pass

    def get_app_settings(self, *args):
        return settings.current_settings['app'][args[0]]

    def set_app_settings(self, *args):
        if settings.set(args[0], args[1]):
            settings.save()
            return args[1]
        else:
            return self.get_app_settings(args[0])

    def get_drive_behavior_code(self, *args):
        pass


def downlink_process(argv):
    self = argv
    while True:
        '''
        Recv data from quecIot or AliYun or other server.
        Data format should be unified at the process module file of its own before put to downlink_queue.

        Data format:
        TODO: =====================
        '''
        data = self.downlink_queue.get()

        DownLinkOptionObj = DownLinkOption(remote_obj=self)
        for option_type, option_data in data:
            for item in option_data:
                model_obj_name = ''
                args = ()
                option_attr = ''
                if option_type == 'set':
                    model_obj_name = item[0]
                    if hasattr(settings.default_values_app, model_obj_name):
                        option_attr = 'set_app_settings'
                        args = item
                    else:
                        option_attr = 'set_' + model_obj_name
                        args = (item[1],)
                elif option_type == 'get':
                    model_obj_name = item
                    if hasattr(settings.default_values_app, model_obj_name):
                        option_attr = 'get_app_settings'
                        args = (item,)
                    else:
                        option_attr = 'get_' + model_obj_name
                else:
                    # TODO: row data
                    pass

                if hasattr(DownLinkOptionObj, option_attr):
                    option_fun = getattr(DownLinkOptionObj, option_attr)
                    option_fun_res = option_fun(*args)
                    self.post_data(self.DATA_NON_LOCA, {model_obj_name: option_fun_res})
                else:
                    # TODO: Raise Error OR Conntinue
                    raise RemoteError('DownLinkOption has no accribute %s.' % option_fun)
        '''
        TODO: processing for settings or control commands from downlink channel
        '''


def uplink_process(argv):
    self = argv
    # ret = False
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
            for key, value in hist.items():
                # Check if non_loca data (sensor or device info data) or location gps data or location non-gps data (cell/wifi-locator data)
                if key == 'non_loca' or key == 'loca_non_gps' or key == 'loca_gps':
                    if key == 'non_loca':
                        data_type = self.DATA_NON_LOCA
                    elif key == 'loca_non_gps':
                        data_type = self.DATA_LOCA_NON_GPS
                    else:
                        data_type = self.DATA_LOCA_GPS
                    for i, data in enumerate(value):
                        ntry = 0
                        # Try at most 3 times to post data to server.
                        while not self.cloud.post_data(data_type, data):
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
                    msg = self.uplink_queue.get()
                    if msg:
                        if msg[0] == self.DATA_NON_LOCA:
                            key = 'non_loca'
                        elif msg[0] == self.DATA_LOCA_NON_GPS:
                            key = 'loca_non_gps'
                        elif msg[0] == self.DATA_LOCA_GPS:
                            key = 'loca_gps'
                        else:
                            continue
                        hist[key].append(msg[1])
                        need_refresh = True
                    else:
                        continue
                else:
                    break
        finally:
            if need_refresh:
                # Flush data in hist-dictionary to tracker_data.hist file.
                self.refresh_history(hist)
                need_refresh = False

            '''
            If history data exists, put a empty msg to uplink_queue to trriger the return of self.uplink_queue.get() API below.
            So that history data could be processed again immediately.
            Without this, history data could only be processed after new data being put into uplink_queue.
            But is this necessary ???
            '''
            if len(hist.get('non_loca', [])) + len(hist.get('loca_non_gps', [])) + len(hist.get('loca_gps', [])):
                self.uplink_queue.put(())

        # When comes to this, wait for new data coming into uplink_queue.
        msg = self.uplink_queue.get()
        if msg:
            if msg[0] == self.DATA_NON_LOCA or msg[0] == self.DATA_LOCA_NON_GPS or msg[0] == self.DATA_LOCA_GPS:
                if not self.cloud.post_data(msg[0], msg[1]):
                    self.add_history(msg[0], msg[1])
                else:
                    continue
            else:
                continue
        else:
            continue


class Remote(object):
    _history = '/usr/tracker_data.hist'

    def __init__(self):
        self.downlink_queue = Queue(maxsize=64)
        self.uplink_queue = Queue(maxsize=64)
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
            self.cloud = QuecThing(dev_info.quecIot['PK'], dev_info.quecIot['PS'], dev_info.quecIot['DK'], dev_info.quecIot['DS'], self.downlink_queue)
            self.DATA_NON_LOCA = DATA_NON_LOCA
            self.DATA_LOCA_NON_GPS = DATA_LOCA_NON_GPS
            self.DATA_LOCA_GPS = DATA_LOCA_GPS
        else:
            raise settings.Error('Current cloud (0x%X) not supported!' % current_settings['sys']['cloud'])

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

    def add_history(self, data_type, data):
        try:
            with open(self._history, 'r') as f:
                res = ujson.load(f)
        except Exception:
            res = {}

        if not isinstance(res, dict):
            res = {}

        if data_type == self.DATA_NON_LOCA:
            key = 'non_loca'
        elif data_type == self.DATA_LOCA_NON_GPS:
            key = 'loca_non_gps'
        elif data_type == self.DATA_LOCA_GPS:
            key = 'loca_gps'

        if key not in res:
            res[key] = []

        res[key].append(data)

        return self.refresh_history(res)

    def refresh_history(self, hist_dict):
        try:
            with open(self._history, 'w') as f:
                ujson.dump(hist_dict, f, indent=4)
                return True
        except Exception:
            return False

    def clean_history(self):
        uos.remove(self._history)

    '''
    Data format to post:

    --- non_loca ---
    {
        'switch': True,
        'energy': 100
    }

    --- loca_non_gps ---
    (117.1138, 31.82279, 550)

    --- loca_gps ---
    ['$GPRMCx,x,x,x', '$GPGGAx,x,x,x']

    '''
    def post_data(self, data_type, data):
        self.uplink_queue.put((data_type, data))
