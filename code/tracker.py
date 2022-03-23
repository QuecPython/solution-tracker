import pm
import utime
import _thread
import sys_bus
import checkNet
import dataCall

from misc import Power
from queue import Queue

import usr.settings as settings

from usr.led import LED
from usr.sensor import Sensor
from usr.remote import Remote
from usr.battery import Battery
from usr.common import numiter
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
        self.low_energy_queue = Queue(maxsize=8)

        self.num_iter = numiter()
        self.num_lock = _thread.allocate_lock()

        self.lpm_fd = None
        _thread.start_new_thread(self.low_energy_work, ())

        if PowerKey is not None:
            self.power_key = PowerKey()
            self.power_key.powerKeyEventRegister(self.pwk_callback)
        if USB is not None:
            self.usb = USB()
            self.usb.setCallback(self.usb_callback)
        dataCall.setCallback(self.nw_callback)

    def get_alert_data(self, alert_code, alert_info):
        alert_data = {}
        if settings.ALERTCODE.get(alert_code):
            current_settings = settings.settings.get()
            alert_status = current_settings.get('app', {}).get('sw_' + settings.ALERTCODE.get(alert_code))
            if alert_status:
                alert_data = {settings.ALERTCODE.get(alert_code): alert_info}
            else:
                log.warn('%s switch is %s' % (settings.ALERTCODE.get(alert_code), alert_status))
        else:
            log.error('altercode (%s) is not exists. alert info: %s' % (alert_code, alert_info))

        return alert_data

    def get_device_data(self, power_switch=True):
        device_data = {}

        loc_info = self.locator.read()
        if loc_info:
            device_data.update(loc_info[1])

        # TODO: Other Machine Info.
        current_settings = settings.settings.get()
        device_data.update({
            'power_switch': power_switch,
            'energy': self.battery.energy(),
            'local_time': utime.mktime(utime.localtime()),
            'ota_status': current_settings['sys']['ota_status'],
        })
        device_data.update(current_settings['app'])

        return device_data

    def get_device_check(self):
        alert_data = []
        alert_code = 20000

        net_check_res = self.check.net_check()
        gps_check_res = self.check.gps_check()
        sensor_check_res = self.check.sensor_check()

        if net_check_res == (3, 1) and gps_check_res and sensor_check_res:
            self.running_led.period = 2
        else:
            self.running_led.period = 0.5
            if net_check_res != (3, 1):
                fault_code = 20001
                alert_info = {'fault_code': fault_code, 'local_time': utime.mktime(utime.localtime())}
                alert_data_res = self.get_alert_data(alert_code, alert_info)
                if alert_data_res:
                    alert_data.append(alert_data_res)
            if not gps_check_res:
                fault_code = 20002
                alert_info = {'fault_code': fault_code, 'local_time': utime.mktime(utime.localtime())}
                alert_data_res = self.get_alert_data(alert_code, alert_info)
                if alert_data_res:
                    alert_data.append(alert_data_res)
            if not sensor_check_res:
                # TODO: Need To Check What Sensor Error To Report.
                pass

        return alert_data

    def get_over_speed_check(self):
        alert_data = {}

        if self.locator.gps:
            speed = self.locator.gps.read_location_GxVTG_speed()
            if speed:
                current_settings = settings.settings.get()
                if float(speed) > current_settings['app']['over_speed_threshold']:
                    alert_code = 30003
                    alert_info = {'local_time': utime.mktime(utime.localtime())}
                    alert_data = self.get_alert_data(alert_code, alert_info)

        return alert_data

    def get_num(self):
        with self.num_lock:
            try:
                num = next(self.num_iter)
            except StopIteration:
                self.num_iter = numiter()
                num = next(self.num_iter)

        return str(num)

    def data_report_cb(self, topic, msg):
        if topic.startswith('wakelock_unlock'):
            pm.wakelock_unlock(self.lpm_fd)
        elif topic.startswith('power_down'):
            self.energy_led.period = None
            self.energy_led.switch(0)
            self.running_led.period = None
            self.running_led.switch(0)
            Power.powerDown()

        sys_bus.unsubscribe(topic)

    def device_data_report(self, power_switch=True, event_data={}, callback=''):
        device_data = self.get_device_data(power_switch)
        if event_data:
            device_data.update(event_data)

        num = self.get_num()
        topic = callback + '_' + num if callback else num
        sys_bus.subscribe(topic, self.data_report_cb)
        self.remote.post_data(topic, device_data)

    def device_check(self):
        device_check_res = self.get_device_check()
        if device_check_res:
            [self.device_data_report(event_data=device_check) for device_check in device_check_res]
        else:
            self.device_data_report()

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
            self.device_check()
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

    def nw_callback(self, args):
        net_check_res = self.check.net_check()
        if args[1] != 1:
            if net_check_res[0] == 0 or (net_check_res[0] == 1 and net_check_res[1] == 0):
                alert_code = 30004
                alert_info = {'local_time': utime.mktime(utime.localtime())}
                alert_data = self.get_alert_data(alert_code, alert_info)
                self.device_data_report(event_data=alert_data)

    def low_energy_work(self):
        while True:
            data = self.low_energy_queue.get()
            if data:
                current_settings = settings.settings.get()
                if current_settings['app']['work_mode'] == settings.default_values_app._work_mode.lowenergy:
                    if self.lpm_fd is None:
                        self.lpm_fd = pm.create_wakelock("tracker_lock", len("tracker_lock"))
                        pm.autosleep(1)
                    pm.wakelock_lock(self.lpm_fd)
                    over_speed_check_res = self.get_over_speed_check()

                    self.device_data_report(event_data=over_speed_check_res, callback='wakelock_unlock')
                else:
                    if self.lpm_fd is not None:
                        pm.autosleep(0)
                        pm.delete_wakelock(self.lpm_fd)
                        self.lpm_fd = None


class SelfCheck(object):

    def net_check(self):
        # return True if OK
        current_settings = settings.settings.get()
        checknet = checkNet.CheckNetwork(settings.PROJECT_NAME, settings.PROJECT_VERSION)
        timeout = current_settings.get('sys', {}).get('checknet_timeout', 60)
        check_res = checknet.wait_network_connected(timeout)
        return check_res

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
