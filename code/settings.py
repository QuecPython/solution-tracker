
import ql_fs
import ujson
import uos
import ure
import _thread
import quecIot
from machine import UART
from usr.common import Singleton

PROJECT_NAME = 'QuecPython_Tracker'

PROJECT_VERSION = '2.0.0'

DATA_NON_LOCA = 0x0
DATA_LOCA_NON_GPS = 0x1
DATA_LOCA_GPS = 0x2

ALERTCODE = {
    20000: 'fault_alert',
    30002: 'low_power_alert',
    30003: 'over_speed_alert',
    30004: 'sim_out_alert',
    30005: 'disassemble_alert',
    40000: 'drive_behavior_alert',
    50001: 'sos_alert',
}

FAULT_CODE = {
    20001: 'net_error',
    20002: 'gps_error',
    20003: 'temp_sensor_error',
    20004: 'light_sensor_error',
    20005: 'move_sensor_error',
    20006: 'mike_error',
}

DRIVE_BEHAVIOR_CODE = {
    40001: 'quick_start',
    40002: 'quick_stop',
    40003: 'quick_turn_left',
    40004: 'quick_turn_right',
}

LOWENERGYMAP = {
    "EC200U": [
        "POWERDOWN",
        "PM",
    ],
    "EC200U": [
        "POWERDOWN",
        "PM",
    ],
    "EC600N": [
        "PM",
    ],
    "EC800G": [
        "PM"
    ],
}

tracker_settings_file = '/usr/tracker_settings.json'

_settings_lock = _thread.allocate_lock()


def settings_lock(func_name):
    def settings_lock_fun(func):
        def wrapperd_fun(*args, **kwargs):
            if not _settings_lock.locked():
                if _settings_lock.acquire():
                    source_fun = func(*args, **kwargs)
                    _settings_lock.release()
                    return source_fun
                else:
                    print('_settings_lock acquire falied. func: %s, args: %s' % (func_name, args))
                    return False
            else:
                print('_settings_lock is locked. func: %s, args: %s' % (func_name, args))
                return False
        return wrapperd_fun
    return settings_lock_fun


class SettingsError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class default_values_app(object):
    '''
    App default settings
    '''

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
        suddenly_start = 0
        suddenly_stop = 1
        suddenly_turn_left = 2
        suddenly_turn_right = 3

    '''
    variables of App default settings below MUST NOT start with '_'
    '''

    phone_num = ''

    loc_method = _loc_method.gps

    work_mode = _work_mode.cycle

    work_cycle_period = 60

    low_power_alert_threshold = 20

    low_power_shutdown_threshold = 5

    over_speed_threshold = 120

    sw_ota = True

    sw_ota_auto_upgrade = True

    sw_voice_listen = False

    sw_voice_record = False

    sw_fault_alert = True

    sw_low_power_alert = True

    sw_over_speed_alert = True

    sw_sim_out_alert = True

    sw_disassemble_alert = True

    sw_drive_behavior_alert = True


class default_values_sys(object):
    '''
    System default settings
    '''

    class _cloud(object):
        none = 0x0
        quecIot = 0x1
        AliYun = 0x2
        JTT808 = 0x4
        customization = 0x8

    class _gps_mode(object):
        none = 0x0
        internal = 0x1
        external = 0x2

    class _ota_status(object):
        none = 0
        to_be_updated = 1
        updating = 2
        update_successed = 3
        update_failed = 4

    class _ali_burning_method(object):
        one_type_one_density = 0
        one_machine_one_density = 1

    '''
    variables of system default settings below MUST NOT start with '_'
    '''
    sw_log = True

    checknet_timeout = 60

    profile_idx = 1

    gps_mode = _gps_mode.external

    ota_status = _ota_status.none

    cloud = _cloud.quecIot

    cloud_init_params = {}

    cloud_timeout = 180

    ali_burning_method = _ali_burning_method.one_machine_one_density

    _quecIot = {
        'PK': 'p11275',
        'PS': 'Q0ZQQndaN3pCUFd6',
        'DK': 'trackdev0304',
        'DS': '8eba9389af434974c3c846d1922d949f',
    }

    _AliYun = {
        'PK': 'guqqtu3edVY',
        'PS': 'xChL7HREtPyYCtPM',
        'DK': 'TrackerEC600N',
        'DS': 'a3153ed0c2f68db6e2f47e0769f966a2',
    }

    _JTT808 = {
        'PK': '',
        'PS': '',
        'DK': '',
        'DS': '',
    }

    locator_init_params = {}

    _gps_cfg = {
        'UARTn': UART.UART1,
        'buadrate': 115200,
        'databits': 8,
        'parity': 0,
        'stopbits': 1,
        'flowctl': 0,
    }

    _cellLocator_cfg = {
        'serverAddr': 'www.queclocator.com',
        'port': 80,
        'token': 'xGP77d2z0i91s67n',
        'timeout': 3,
        'profileIdx': profile_idx,
    }

    _wifiLocator_cfg = {
        'token': 'xGP77d2z0i91s67n'
    }

    @staticmethod
    def _get_locator_init_params(loc_method):
        locator_init_params = {}

        if loc_method & default_values_app._loc_method.gps:
            locator_init_params['gps_cfg'] = default_values_sys._gps_cfg
        if loc_method & default_values_app._loc_method.cell:
            locator_init_params['cellLocator_cfg'] = default_values_sys._cellLocator_cfg
        if loc_method & default_values_app._loc_method.wifi:
            locator_init_params['wifiLocator_cfg'] = default_values_sys._wifiLocator_cfg

        return locator_init_params

    @staticmethod
    def _get_cloud_init_params(cloud):
        cloud_init_params = {}

        if cloud & default_values_sys._cloud.quecIot:
            cloud_init_params = default_values_sys._quecIot
            cloud_init_params = default_values_sys._quecIot_init_params(cloud_init_params)
        if cloud & default_values_sys._cloud.AliYun:
            cloud_init_params = default_values_sys._AliYun
        if cloud & default_values_sys._cloud.JTT808:
            cloud_init_params = default_values_sys._JTT808

        return cloud_init_params

    @staticmethod
    def _quecIot_init_params(cloud_init_params):
        if not cloud_init_params['DK'] or not cloud_init_params['DS']:
            if quecIot.init():
                if quecIot.setProductinfo(cloud_init_params['PK'], cloud_init_params['PS']):
                    if quecIot.setDkDs(cloud_init_params['DK'], cloud_init_params['DS']):
                        ndk, nds = quecIot.getDkDs()
                        cloud_init_params['DK'] = ndk
                        cloud_init_params['DS'] = nds
        return cloud_init_params


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
                    'sw_sim_out_alert', 'sw_disassemble_alert', 'sw_drive_behavior_alert'):
                if not isinstance(val, bool):
                    return False
                self.current_settings['app'][opt] = val
                return True

            else:
                return False
        if opt in self.current_settings['sys']:
            if opt == 'sw_log':
                if not isinstance(val, bool):
                    return False
                self.current_settings['app'][opt] = val
                return True
            elif opt == 'ota_status':
                if not isinstance(val, int):
                    return False
                self.current_settings['app'][opt] = val
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
