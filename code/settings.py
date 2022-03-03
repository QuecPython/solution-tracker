
import ql_fs
import ujson
import uos
import ure

tracker_settings_file = '/usr/tracker_settings.json'

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

    '''
    variables of App default settings below MUST NOT start with '_'
    '''

    phone_num = ''

    loc_method = _loc_method.gps

    loc_mode = _loc_mode.cycle

    loc_cycle_period = 1

    sw_ota = True

    sw_auto_upgrade = True 

    sw_electric_fence = True

    sw_phone_call = False

    sw_voice_record = False

    sw_jtt808 = True

    sw_fault_alert = True

    sw_low_power_alert = True

    sw_over_speed_alert = True

    sw_sim_out_alert = True

    sw_disassemble_alert = True

    sw_vibrate_alert = True

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

    cloud = _cloud.quecIot


default_settings_app = {k:v for k,v in default_values_app.__dict__.items() if not k.startswith('_')}
current_settings_app = {}

default_settings_sys = {k:v for k,v in default_values_sys.__dict__.items() if not k.startswith('_')}
current_settings_sys = {}

default_settings = {'app':default_settings_app, 'sys':default_settings_sys}
current_settings = {}

def init():
    global current_settings
    if not ql_fs.path_exists(tracker_settings_file):
        with open(tracker_settings_file, 'w') as f:
            ujson.dump(default_settings, f, indent = 4)
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

        elif opt == 'sw_ota' or opt == 'sw_auto_upgrade' or opt == 'sw_electric_fence' or opt == 'sw_phone_call' or opt == 'sw_voice_record' \
        or opt == 'sw_jtt808' or opt == 'sw_fault_alert' or opt == 'sw_low_power_alert' or opt == 'sw_over_speed_alert' or opt == 'sw_sim_out_alert' \
        or opt == 'sw_disassemble_alert' or opt == 'sw_vibrate_alert' or opt == 'sw_drive_behavior_alert':
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
        ujson.dump(current_settings, f, indent = 4)

def reset():
    uos.remove(tracker_settings_file)

class Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
