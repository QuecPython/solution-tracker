
import usr.settings as settings
from usr.tracker import Tracker
from usr.logging import getLogger
import UART
import osTimer

tracker = None

log = getLogger('tracker')

PROFILE_IDX = 0

settings.init()
current_settings = settings.get()

locator_init_params = {}

if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.gps:
    locator_init_params['gps_cfg'] = {
        'UARTn': UART.UART0,
        'buadrate': 115200,
        'databits': 8,
        'parity': 0,
        'stopbits': 1,
        'flowctl': 0
    }

if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.cell:
    locator_init_params['cellLocator_cfg'] = {
        'serverAddr': 'www.queclocator.com',
        'port': 80,
        'token': 'xGP77d2z0i91s67n',
        'timeout': 3,
        'profileIdx': PROFILE_IDX
    }

if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.wifi:
    locator_init_params['wifiLocator_cfg'] = {
        'token': 'xGP77d2z0i91s67n'
    }

def loc_read_cb(data):
    if data:
        loc_method = data[0]
        loc_data = data[1]
        log.info("loc_method:", loc_method)
        log.info("loc_data:", loc_data)
        if loc_method == settings.default_values_app._loc_method.gps:
            data_type = tracker.remote.DATA_LOCA_GPS
        else:
            data_type = tracker.remote.DATA_LOCA_NON_GPS
        tracker.remote.post_data(data_type, loc_data)

tracker = Tracker(loc_read_cb, **locator_init_params)

def loc_timer_cb(argv):
    tracker.trigger()

if (current_settings['app']['loc_mode'] & settings.default_values_app._loc_mode.cycle) and current_settings['app']['loc_cycle_period']:
    loc_timer = osTimer()
    loc_timer.start(current_settings['app']['loc_cycle_period'] * 1000, 1, loc_timer_cb)
