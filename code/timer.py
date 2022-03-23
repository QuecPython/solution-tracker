import utime
import osTimer

import usr.settings as settings
from usr.common import Singleton
from usr.logging import getLogger

try:
    from misc import USB
except ImportError:
    USB = None

log = getLogger(__name__)


class TrackerTimer(Singleton):

    def __init__(self, tracker):
        self.tracker = tracker
        self.tracker_timer = osTimer()
        self.tracker_timer.start(1000, 1, self.timer_callback)
        self.loc_count = 0
        self.battery_count = 0
        self.gnss_count = 0
        self.quec_ota = 0

    def timer_callback(self, args):
        current_settings = settings.settings.get()

        self.loc_count += 1
        self.battery_count += 1
        self.gnss_count += 1
        self.quec_ota += 1

        if (current_settings['app']['work_mode'] != settings.default_values_app._work_mode.none) \
                and current_settings['app']['work_cycle_period'] \
                and self.loc_count >= current_settings['app']['work_cycle_period']:
            self.loc_count = 0
            self.loc_timer()

        if self.battery_count >= 60:
            self.battery_count = 0
            self.battery_timer()

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.gps and \
                current_settings['sys']['gps_mode'] & settings.default_values_sys._gps_mode.internal:
            self.gnss_count = 0
            self.gnss_timer()

        if current_settings['app']['sw_ota'] is False:
            self.quec_ota = 0
        if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot and \
                self.quec_ota >= 3600:
            self.quec_ota = 0
            self.quecthing_ota_timer()

    def loc_timer(self):
        current_settings = settings.settings.get()
        if current_settings['app']['work_mode'] == settings.default_values_app._work_mode.intelligent:
            if not self.tracker.locator.gps:
                if not self.tracker.locator.gps.read_location_GxVTG_speed():
                    return
                elif float(self.tracker.locator.gps.read_location_GxVTG_speed()) <= 0:
                    return
            else:
                return
        elif current_settings['app']['work_mode'] == settings.default_values_app._work_mode.lowenergy:
            self.tracker.low_energy_queue.put(True)
            return

        over_speed_check_res = self.tracker.get_over_speed_check()
        self.tracker.device_data_report(event_data=over_speed_check_res)

    def battery_timer(self):
        current_settings = settings.settings.get()
        energy = self.tracker.battery.energy()
        is_charge = USB().getStatus() if USB is not None else 1
        if is_charge == 0:
            self.tracker.energy_led_show(energy)
            if current_settings['app']['sw_low_power_alert']:
                if energy <= current_settings['app']['low_power_alert_threshold']:
                    alert_data = self.tracker.get_alert_data(30002, {'local_time': utime.mktime(utime.localtime())})
                    self.tracker.device_data_report(event_data=alert_data)
            if energy <= current_settings['app']['low_power_shutdown_threshold']:
                self.tracker.device_data_report(power_switch=False, callback='power_down')
        elif is_charge == 1:
            self.tracker.energy_led_show(energy)

    def gnss_timer(self):
        self.tracker.locator.gps.quecgnss_read()

    def quecthing_ota_timer(self):
        self.tracker.remote.check_ota()


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
