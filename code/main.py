
import osTimer
import usr.settings as settings
from usr.tracker import Tracker
from usr.logging import getLogger

log = getLogger(__name__)

tracker = None

PROFILE_IDX = 0


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

tracker = Tracker(loc_read_cb, **settings.locator_init_params)


def loc_timer_cb(argv):
    tracker.trigger()


if __name__ == '__main__':
    settings.init()
    # current_settings, locator_init_params = settings.get()

    if (settings.current_settings['app']['loc_mode'] & settings.default_values_app._loc_mode.cycle) \
            and settings.current_settings['app']['loc_cycle_period']:
        loc_timer = osTimer()
        loc_timer.start(settings.current_settings['app']['loc_cycle_period'] * 1000, 1, loc_timer_cb)
