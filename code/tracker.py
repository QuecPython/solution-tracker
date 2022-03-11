# import _thread

# from queue import Queue
from machine import Timer
from misc import USB
from misc import Power
from misc import PowerKey

import usr.settings as settings

from usr.led import LED
from usr.sensor import Sensor
from usr.remote import Remote
from usr.battery import Battery
from usr.common import Singleton, Controller
from usr.location import Location
from usr.alert import AlertMonitor
from usr.logging import getLogger
from usr.selfcheck import net_check, gps_check, sensor_check

log = getLogger(__name__)


class Tracker(Singleton):
    def __init__(self, *args, **kwargs):
        self.led = LED()
        self.sensor = Sensor()
        self.remote = Remote(self.remote_read_cb)
        self.locator = Location(self.loc_read_cb)
        self.alert = AlertMonitor(self.alert_read_cb)
        self.battery = Battery(self.batter_read_cb)
        self.controller = Controller(self.remote)

        current_settings = settings.settings.get()
        self.loc_timer = Timer(current_settings['sys']['loc_timern'])
        self.loc_timer_init()

        self.power_key = PowerKey()
        self.power_key.powerKeyEventRegister(self.pwk_callback)
        self.usb = USB()
        self.usb.setCallback(self.usb_callback)

    def remote_read_cb(self, *data):
        if data:
            if data[0] == 'object_model':
                for item in data[1]:
                    if item[0] == 'loc_mode':
                        self.loc_timer_init()

    def loc_read_cb(self, data):
        if data:
            loc_method = data[0]
            loc_data = data[1]
            log.info("loc_method:", loc_method)
            log.info("loc_data:", loc_data)
            if loc_method == settings.default_values_app._loc_method.gps:
                data_type = self.remote.DATA_LOCA_GPS
            else:
                data_type = self.remote.DATA_LOCA_NON_GPS
            self.remote.post_data(data_type, loc_data)

    def alert_read_cb(self, *data):
        if data:
            data_type = self.remote.DATA_NON_LOCA
            alert_data = {data[0]: data[1]}
            self.remote.post_data(data_type, alert_data)

    def batter_read_cb(self, *data):
        current_settings = settings.settings.get()
        energy = data[0]
        is_charge = USB.getStatus()
        if is_charge == 0:
            self.energy_led_show(energy)
            if current_settings['app']['sw_low_power_alert']:
                if energy <= current_settings['app']['low_power_alert_threshold']:
                    # TODO: low_power_alert
                    pass
            if energy <= current_settings['app']['low_power_shutdown_threshold']:
                # TODO: low_power_shutdown
                self.led.off()
                Power.powerDown()
        elif is_charge == 1:
            if energy == 100:
                self.led.flashing_mode('energy_led', 0, 'green')

    def machine_info_report(self):
        pass

    def energy_led_show(self, energy):
        color = None
        if energy <= 5:
            self.led.off()
        elif 5 < energy <= 20:
            color = 'red'
        elif 20 < energy <= 40:
            color = 'orange'
        elif 40 < energy <= 70:
            color = 'yellow'
        elif 70 < energy <= 100:
            color = 'green'
        if color:
            self.led.flashing_mode('energy_led', 0, color)

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

    def pwk_callback(self, status):
        if status == 0:
            # TODO: Power On SelfCheck
            log.info('PowerKey Release.')
            net_check_res = net_check()
            gps_check_res = gps_check()
            sensor_check_res = sensor_check()
            if net_check_res and gps_check_res and sensor_check_res:
                self.led.flashing_mode('operating_led', 2000)
            else:
                self.led.flashing_mode('operating_led', 500)
                # TODO: Post Fault Error Info
        elif status == 1:
            log.info('PowerKey Press.')
        else:
            log.warn('Unknown PowerKey Status:', status)

    def usb_callback(self, status):
        energy = self.battery.energy()
        if status == 0:
            log.info('USB is disconnected.')
            self.energy_led_show(energy)
        elif status == 1:
            log.info('USB is connected.')
            if energy <= 5:
                self.led.flashing_mode('energy_led', 1000, 'red')
            elif 5 < energy < 100:
                self.led.flashing_mode('energy_led', 1000, 'yellow')
            elif energy == 100:
                self.led.flashing_mode('energy_led', 0, 'green')
        else:
            log.warn('Unknown USB Stauts:', status)
