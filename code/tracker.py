import _thread

from queue import Queue
from machine import Timer
from usr.logging import getLogger

import usr.settings as settings

# from usr.led import LED
# from usr.sensor import Sensor
from usr.remote import Remote
from usr.location import Location
from usr.alert import AlertMonitor
from usr.common import Singleton

log = getLogger(__name__)


def tracker_worker(args):
    self = args
    while True:
        data = self.tracker_command_queue.get()
        if data == 'loc_mode':
            self.loc_timer_init()


class Tracker(Singleton):
    def __init__(self, remote_read_cb, loc_read_cb, alert_read_cb, **kw):
        # self.led = LED()
        # self.sensor = Sensor()
        self.remote = Remote(remote_read_cb)
        self.locator = Location(loc_read_cb)
        self.alert = AlertMonitor(alert_read_cb)

        self.loc_timer = Timer(Timer.Timer0)
        self.tracker_command_queue = Queue(maxsize=64)
        _thread.start_new_thread(tracker_worker, (self,))

        self.loc_timer_init()

    def loc_timer_cb(self, args):
        self.locator.trigger()

    def loc_timer_init(self):
        current_settings = settings.settings.get()
        if (current_settings['app']['loc_mode'] & settings.default_values_app._loc_mode.cycle) \
                and current_settings['app']['loc_cycle_period']:
            log.debug('[.] loc_timer to restart.')
            self.loc_timer.stop()
            log.debug('[.] loc_timer stop.')
            self.loc_timer.start(period=current_settings['app']['loc_cycle_period'] * 1000, mode=self.loc_timer.PERIODIC, callback=self.loc_timer_cb)
            log.debug('[.] loc_timer start.')
        else:
            self.loc_timer.stop()
            log.debug('[.] loc_timer stop forever.')
