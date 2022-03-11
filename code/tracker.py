import sim
import net
import utime

from misc import USB
from misc import PowerKey

import usr.settings as settings

from usr.led import LED
from usr.sensor import Sensor
from usr.remote import Remote
from usr.battery import Battery
from usr.common import Singleton
from usr.alert import AlertMonitor
from usr.logging import getLogger
from usr.location import Location, GPS
from usr.timer import TrackerTimer, LEDTimer

log = getLogger(__name__)


class Tracker(Singleton):
    def __init__(self, *args, **kwargs):
        self.energy_led = LED()
        self.running_led = LED()
        self.sensor = Sensor()
        self.locator = Location(self.loc_read_cb)
        self.alert = AlertMonitor(self.alert_read_cb)
        self.battery = Battery()
        self.remote = Remote(self)

        self.power_key = PowerKey()
        self.power_key.powerKeyEventRegister(self.pwk_callback)
        self.usb = USB()
        self.usb.setCallback(self.usb_callback)
        self.check = SelfCheck()
        self.tracker_timer = TrackerTimer(self)
        self.led_timer = LEDTimer(self)

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

    def machine_info_report(self, power_switch=True, block_io=False):
        current_settings = settings.settings.get()
        self.locator.trigger()
        # TODO: Other Machine Info.
        machine_info = {
            'power_switch': power_switch,
            'energy': self.battery.energy(),
            'local_time': utime.mktime(utime.localtime())
        }
        machine_info.update(current_settings['app'])
        if block_io is True:
            self.remote.set_block_io(block_io)
        self.remote.post_data(self.remote.DATA_NON_LOCA, machine_info)
        if self.remote.block_io is True:
            self.remote.set_block_io(False)

    def energy_led_show(self, energy):
        current_settings = settings.settings.get()
        if energy <= current_settings['app']['low_power_shutdown_threshold']:
            self.energy_led.period = None
            self.energy_led.switch(0)
        elif current_settings['app']['low_power_shutdown_threshold'] < energy <= current_settings['app']['low_power_alert_threshold']:
            self.energy_led.period = 1
        elif current_settings['app']['low_power_alert_threshold'] < energy:
            self.energy_led.period = 0

    def machine_check(self):
        net_check_res = self.check.net_check()
        gps_check_res = self.check.gps_check()
        sensor_check_res = self.check.sensor_check()
        if net_check_res and gps_check_res and sensor_check_res:
            self.running_led.period = 2
        else:
            self.running_led.period = 0.5
            if not net_check_res:
                self.alert.post_alert(20000, {'fault_code': 20001})
            if not gps_check_res:
                self.alert.post_alert(20000, {'fault_code': 20002})
            if not sensor_check_res:
                # TODO: Need To Check What Sensor Error To Report.
                pass
        self.machine_info_report()

    def pwk_callback(self, status):
        if status == 0:
            log.info('PowerKey Release.')
            self.machine_check()
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
            self.energy_led_show(energy)
        else:
            log.warn('Unknown USB Stauts:', status)


class SelfCheck(object):
    def net_check(self):
        # return True if OK
        if sim.getStatus() == 1:
            if net.getModemFun() == 1:
                return True

        return False

    def gps_check(self):
        # return True if OK
        gps = GPS(settings.default_values_sys._gps_cfg)

        retry = 0
        gps_data = None
        sleep_time = 1
        while retry < 5:
            gps_data = gps.read()
            if gps_data:
                break
            else:
                retry += 1
                utime.sleep(sleep_time)
                sleep_time *= 2
        if gps_data:
            return True

        return False

    def sensor_check(self):
        # return True if OK
        # TODO: How To Check Light & Movement Sensor?
        return True
