
import ql_fs
import ujson
import uos
import ure
from machine import UART

tracker_settings_file = '/usr/tracker_settings.json'

current_settings = {}
current_settings_app = {}
current_settings_sys = {}


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

    class _loc_mode(object):
        none = 0x0
        cycle = 0x1
        onAlert = 0x2
        onPhoneCall = 0x4
        onVoiceRecord = 0x8
        all = 0xF

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

    loc_mode = _loc_mode.cycle

    loc_cycle_period = 1

    low_power_alert_threshold = 20

    low_power_shutdown_threshold = 5

    sw_ota = True

    sw_auto_upgrade = True

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

    '''
    variables of system default settings below MUST NOT start with '_'
    '''
    profile_idx = 0

    cloud = _cloud.quecIot

    locator_init_params = {}

    _gps_cfg = {
        'UARTn': UART.UART0,
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


def init():
    global current_settings

    if default_values_app.loc_method & default_values_app._loc_method.gps:
        default_values_sys.locator_init_params = default_values_sys._gps_cfg
    elif default_values_app.loc_method & default_values_app._loc_method.cell:
        default_values_sys.locator_init_params = default_values_sys._cellLocator_cfg
    elif default_values_app.loc_method & default_values_app._loc_method.wifi:
        default_values_sys.locator_init_params = default_values_sys._wifiLocator_cfg

    default_settings_app = {k: v for k, v in default_values_app.__dict__.items() if not k.startswith('_')}
    default_settings_sys = {k: v for k, v in default_values_sys.__dict__.items() if not k.startswith('_')}
    default_settings = {'app': default_settings_app, 'sys': default_settings_sys}

    if not ql_fs.path_exists(tracker_settings_file):
        with open(tracker_settings_file, 'w') as f:
            ujson.dump(default_settings, f)
        current_settings = dict(default_settings)
    else:
        with open(tracker_settings_file, 'r') as f:
            current_settings = ujson.load(f)


def get():
    global current_settings
    return current_settings


def set(opt, val):
    if opt in current_settings['app']:
        if opt == 'phone_num':
            if not isinstance(val, str):
                return False
            pattern = ure.compile(r'^(?:(?:\+)86)?1[3-9]\d{9}$')
            if pattern.search(val):
                current_settings['app'][opt] = val
                return True
            return False

        elif opt == 'loc_method':
            if not isinstance(val, int):
                return False
            if val > default_values_app._loc_method.all:
                return False
            current_settings['app'][opt] = val
            return True

        elif opt == 'loc_mode':
            if not isinstance(val, int):
                return False
            if val > default_values_app._loc_mode.all:
                return False
            current_settings['app'][opt] = val
            return True

        elif opt == 'loc_cycle_period':
            if not isinstance(val, int):
                return False
            if val < 1:
                return False
            current_settings['app'][opt] = val
            return True
        elif opt == 'low_power_alert_threshold' or opt == 'low_power_shutdown_threshold':
            if not isinstance(val, int):
                return False
            if val < 0 or val > 100:
                return False
            current_settings['app'][opt] = val
            return True
        elif opt in (
                'sw_ota', 'sw_auto_upgrade', 'sw_electric_fence', 'sw_phone_call',
                'sw_voice_record', 'sw_jtt808', 'sw_fault_alert', 'sw_low_power_alert',
                'sw_over_speed_alert', 'sw_sim_out_alert', 'sw_disassemble_alert',
                'sw_vibrate_alert', 'sw_drive_behavior_alert'):
            if not isinstance(val, bool):
                return False
            current_settings['app'][opt] = val
            return True

        else:
            return False

    else:
        return False


def save():
    with open(tracker_settings_file, 'w') as f:
        ujson.dump(current_settings, f, indent=4)


def reset():
    uos.remove(tracker_settings_file)


class Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
