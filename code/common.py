import utime
import _thread
import osTimer

from misc import USB
from misc import Power

import usr.settings as settings
from usr.battery import Battery


class Singleton(object):
    _instance_lock = _thread.allocate_lock()

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance_dict'):
            Singleton.instance_dict = {}

        if str(cls) not in Singleton.instance_dict.keys():
            with Singleton._instance_lock:
                _instance = super().__new__(cls)
                Singleton.instance_dict[str(cls)] = _instance

        return Singleton.instance_dict[str(cls)]


class ControllerError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Controller(Singleton):
    def __init__(self, tracker):
        self.tracker = tracker

    def power_switch(self, perm, flag=None, *args):
        if perm == 'r':
            self.tracker.remote.post_data(self.tracker.remote.DATA_NON_LOCA, {'power_switch': True})
        elif perm == 'w':
            if flag is True:
                self.tracker.machine_info_report()
            elif flag is False:
                self.tracker.machine_info_report(power_switch=flag)
                self.tracker.energy_led.period = None
                self.tracker.energy_led.switch(0)
                self.tracker.running_led.period = None
                self.tracker.running_led.switch(0)
                Power.powerDown()
        else:
            raise ControllerError('Controller switch permission error %s.' % perm)

    def energy(self, perm, *args):
        if perm == 'r':
            battery_energy = Battery().energy()
            self.tracker.remote.post_data(self.tracker.remote.DATA_NON_LOCA, {'energy': battery_energy})
        else:
            raise ControllerError('Controller energy permission error %s.' % perm)


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
                and self.loc_count == current_settings['app']['loc_cycle_period']:
            self.loc_count = 0
            self.loc_timer()

        if self.barrery_count == 60:
            self.barrery_count = 0
            self.barrery_timer()

        if current_settings['app']['loc_method'] & settings.default_values_app._loc_method.gps and \
                current_settings['app']['gps_mode'] & settings.default_values_app._gps_mode.internal:
            self.gnns_count = 1
            self.gnns_timer()

    def loc_timer(self):
        self.tracker.locator.trigger()

    def barrery_timer(self):
        current_settings = settings.settings.get()
        energy = self.tracker.battery.energy()
        is_charge = USB.getStatus()
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


class LEDTimer(object):
    def __init__(self, tracker):
        self.period = 500
        self.tracker = tracker
        self.energy_led_count = 0
        self.running_led_count = 0
        self.led_timer = osTimer(self.period, 1, self.led_callback)

    def led_callback(self):
        self.energy_led_count += 1
        self.running_led_count += 1

        if self.tracker.energy_led.period == 0 or \
                (self.tracker.energy_led.period > 0 and int(self.tracker.energy_led.period / self.period) == self.energy_led_count):
            self.led_timer(self.tracker.energy_led)

        if self.tracker.running_led.period == 0 or \
                (self.tracker.running_led.period > 0 and int(self.tracker.energy_led.period / self.period) == self.running_led_count):
            self.led_timer(self.tracker.running_led)

    def led_timer(self, led):
        led.switch(1)
        if led.period > 0:
            led.switch()
