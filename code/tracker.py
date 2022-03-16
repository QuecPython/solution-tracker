import utime
import checkNet

import usr.settings as settings

from usr.led import LED
from usr.sensor import Sensor
from usr.remote import Remote
from usr.battery import Battery
from usr.common import Singleton
from usr.logging import getLogger
from usr.location import Location, GPS
from usr.timer import TrackerTimer, LEDTimer

try:
    from misc import USB
except ImportError:
    USB = None
try:
    from misc import PowerKey
except ImportError:
    PowerKey = None


log = getLogger(__name__)


class Tracker(Singleton):
    def __init__(self, *args, **kwargs):
        self.check = SelfCheck()

        self.energy_led = LED()
        self.running_led = LED()
        self.sensor = Sensor()
        self.locator = Location()
        self.battery = Battery()
        self.remote = Remote(self)

        self.tracker_timer = TrackerTimer(self)
        self.led_timer = LEDTimer(self)

        if PowerKey is not None:
            self.power_key = PowerKey()
            self.power_key.powerKeyEventRegister(self.pwk_callback)
        if USB is not None:
            self.usb = USB()
            self.usb.setCallback(self.usb_callback)

    def loc_report(self):
        data = None
        retry = 0
        while retry < 3:
            data = self.locator.read()
            if data:
                break
            else:
                retry += 1
                utime.sleep(1)

        if data:
            loc_method = data[0]
            loc_data = data[1]
            if loc_method == settings.default_values_app._loc_method.gps:
                data_type = self.remote.DATA_LOCA_GPS
            else:
                data_type = self.remote.DATA_LOCA_NON_GPS

            current_settings = settings.settings.get()
            if current_settings['sys']['cloud'] == settings.default_values_sys._cloud.quecIot:
                if loc_method == settings.default_values_app._loc_method.cell:
                    loc_data = ['LBS']
                elif loc_method == settings.default_values_app._loc_method.wifi:
                    loc_data = []

            return self.remote.post_data(data_type, loc_data)
        else:
            log.warn('Location data is not ready.')

        return False

    def alert_report(self, alert_code, alert_info):
        if settings.ALERTCODE.get(alert_code):
            current_settings = settings.settings.get()
            alert_status = current_settings.get('app', {}).get('sw_' + settings.ALERTCODE.get(alert_code))
            if alert_status:
                data_type = self.remote.DATA_NON_LOCA
                alert_data = {settings.ALERTCODE.get(alert_code): alert_info}
                return self.remote.post_data(data_type, alert_data)
            else:
                log.warn('%s status is %s' % (settings.ALERTCODE.get(alert_code), alert_status))
        else:
            log.error('altercode (%s) is not exists. alert info: %s' % (alert_code, alert_info))

        return False

    def machine_info_report(self, power_switch=True):
        if self.loc_report():
            # TODO: Other Machine Info.
            current_settings = settings.settings.get()
            machine_info = {
                'power_switch': power_switch,
                'energy': self.battery.energy(),
                'local_time': utime.mktime(utime.localtime()),
                'ota_status': current_settings['sys']['ota_status']
            }
            machine_info.update(current_settings['app'])
            return self.remote.post_data(self.remote.DATA_NON_LOCA, machine_info)

        return False

    def machine_check(self):
        net_check_res = self.check.net_check()
        gps_check_res = self.check.gps_check()
        sensor_check_res = self.check.sensor_check()

        alert_code = 20000
        fault_code = 0
        if net_check_res and gps_check_res and sensor_check_res:
            self.running_led.period = 2
        else:
            self.running_led.period = 0.5
            if not net_check_res:
                fault_code = 20001
                alert_info = {'fault_code': fault_code, 'local_time': utime.mktime(utime.localtime())}
            if not gps_check_res:
                fault_code = 20002
                alert_info = {'fault_code': fault_code, 'local_time': utime.mktime(utime.localtime())}
            if not sensor_check_res:
                # TODO: Need To Check What Sensor Error To Report.
                pass

            self.alert_report(alert_code, alert_info)
        self.machine_info_report()

        return fault_code

    def energy_led_show(self, energy):
        current_settings = settings.settings.get()
        if energy <= current_settings['app']['low_power_shutdown_threshold']:
            self.energy_led.period = None
            self.energy_led.switch(0)
        elif current_settings['app']['low_power_shutdown_threshold'] < energy <= current_settings['app']['low_power_alert_threshold']:
            self.energy_led.period = 1
        elif current_settings['app']['low_power_alert_threshold'] < energy:
            self.energy_led.period = 0

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
        current_settings = settings.settings.get()
        checknet = checkNet.CheckNetwork(settings.PROJECT_NAME, settings.PROJECT_VERSION)
        timeout = current_settings.get('sys', {}).get('checknet_timeout', 60)
        check_res = checknet.wait_network_connected(timeout)
        if check_res == (3, 1):
            return True
        else:
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
