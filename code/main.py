
import osTimer
import usr.settings as settings
from usr.tracker import Tracker
from usr.logging import getLogger

log = getLogger(__name__)

PROJECT_NAME = 'QuecPython_Tracker'

PROJECT_VERSION = '2.0.0'

tracker = None

current_settings = settings.settings.get()


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


def alert_read_cb(data):
    if data:
        data_type = tracker.remote.DATA_NON_LOCA
        alert_data = {data[0]: data[1]}
        tracker.remote.post_data(data_type, alert_data)


tracker = Tracker(loc_read_cb, alert_read_cb)


def loc_timer_cb(argv):
    tracker.locator.trigger()


if __name__ == '__main__':
    if (current_settings['app']['loc_mode'] & settings.default_values_app._loc_mode.cycle) \
            and current_settings['app']['loc_cycle_period']:
        loc_timer = osTimer()
        loc_timer.start(current_settings['app']['loc_cycle_period'] * 1000, 1, loc_timer_cb)
