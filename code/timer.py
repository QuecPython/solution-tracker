import utime
import osTimer

from misc import USB
from misc import Power

import usr.settings as settings
from usr.common import Singleton
from usr.logging import getLogger

log = getLogger(__name__)


class TrackerTimer(Singleton):

    def __init__(self, tracker):
        self.tracker = tracker
        self.tracker_timer = osTimer()
        self.tracker_timer.start(1000, 1, self.timer_callback)
        self.loc_count = 0
        self.barrery_count = 0
        self.gnns_count = 0

    def timer_callback(self, args):
        current_settings = settings.settings.get()

        self.loc_count += 1
        self.barrery_count += 1
        self.gnns_count += 1

        if (current_settings['app']['loc_mode'] & settings.default_values_app._loc_mode.cycle) \
                and current_settings['app']['loc_cycle_period'] \
                and self.loc_count >= current_settings['app']['loc_cycle_period']:
            self.loc_count = 0
            self.loc_timer()

        if self.barrery_count == 60:
            self.barrery_count = 0
            self.barrery_timer()

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.gps and \
                current_settings['app']['gps_mode'] & settings.default_values_app._gps_mode.internal:
            self.gnns_count = 0
            self.gnns_timer()

    def loc_timer(self):
        self.tracker.locator.trigger()

    def barrery_timer(self):
        log.debug('start barrery_timer')
        current_settings = settings.settings.get()
        energy = self.tracker.battery.energy()
        is_charge = USB().getStatus()
        if is_charge == 0:
            self.tracker.energy_led_show(energy)
            if current_settings['app']['sw_low_power_alert']:
                if energy <= current_settings['app']['low_power_alert_threshold']:
                    self.tracker.alert.post_alert(30002, {'local_time': utime.mktime(utime.localtime())})
                    self.tracker.machine_info_report()
            if energy <= current_settings['app']['low_power_shutdown_threshold']:
                self.tracker.machine_info_report(power_switch=False)
                self.tracker.energy_led.period = None
                self.tracker.energy_led.switch(0)
                self.tracker.running_led.period = None
                self.tracker.running_led.switch(0)
                Power.powerDown()
        elif is_charge == 1:
            self.tracker.energy_led_show(energy)

    def gnns_timer(self):
        self.tracker.locator.gps.quecgnns_read()


class LEDTimer(Singleton):
    def __init__(self, tracker):
        self.period = 500
        self.tracker = tracker
        self.energy_led_count = 0
        self.running_led_count = 0
        self.led_timer = osTimer()
        self.led_timer.start(self.period, 1, self.led_callback)

    def led_callback(self, args):
        self.energy_led_count += 1
        self.running_led_count += 1

        if self.tracker.energy_led.period is not None:
            if self.tracker.energy_led.period == 0 or \
                    (self.tracker.energy_led.period > 0 and int(self.tracker.energy_led.period / self.period) <= self.energy_led_count):
                self.led_switch(self.tracker.energy_led)

        if self.tracker.running_led.period is not None:
            if self.tracker.running_led.period == 0 or \
                    (self.tracker.running_led.period > 0 and int(self.tracker.running_led.period / self.period) <= self.running_led_count):
                self.led_switch(self.tracker.running_led)

    def led_switch(self, led):
        if led.period == 0:
            led.switch(1)
        else:
            led.switch()
