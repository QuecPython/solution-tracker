# Copyright (c) Quectel Wireless Solution, Co., Ltd.All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pm
import utime
import _thread
import sys_bus
import checkNet
import dataCall

from misc import Power

import usr.settings as settings

from usr.led import LED
from usr.sensor import Sensor
from usr.remote import Remote
from usr.battery import Battery
from usr.common import numiter
from usr.common import Singleton
from usr.mpower import PowerManage
from usr.logging import getLogger
from usr.location import GPS
from usr.location import Location
from usr.timer import LEDTimer

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
        self.net_enable = True
        self.num_iter = numiter()
        self.num_lock = _thread.allocate_lock()

        self.check = SelfCheck()
        self.energy_led = LED()
        self.running_led = LED()
        self.sensor = Sensor()
        self.locator = Location()
        self.battery = Battery()
        self.remote = Remote(self)
        self.power_manage = PowerManage(self)

        self.led_timer = LEDTimer(self)
        # self.energy = 100
        # self.cenergy = -10

        if PowerKey is not None:
            self.power_key = PowerKey()
            self.power_key.powerKeyEventRegister(self.pwk_callback)
        if USB is not None:
            self.usb = USB()
            self.usb.setCallback(self.usb_callback)
        dataCall.setCallback(self.nw_callback)

    def get_local_time(self):
        return str(utime.mktime(utime.localtime()) * 1000)

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
            log.debug('loc_method: %s' % loc_info[0])
            device_data.update(loc_info[1])

        current_settings = settings.settings.get()

        # TODO: Test Energy
        # if self.energy <= 10:
        #     self.cenergy = 10
        # if self.energy >= 100:
        #     self.cenergy = -10
        # self.energy = self.energy + self.cenergy
        # energy = self.energy

        energy = self.battery.energy()
        if energy <= current_settings['app']['low_power_alert_threshold']:
            alert_data = self.get_alert_data(30002, {'local_time': self.get_local_time()})
            device_data.update(alert_data)

        # TODO: Other Machine Info.
        device_data.update({
            'power_switch': power_switch,
            'energy': energy,
            'local_time': self.get_local_time(),
            'ota_status': current_settings['sys']['ota_status'],
            'drive_behavior_code': current_settings['sys']['drive_behavior_code'],
        })
        device_data.update(current_settings['app'])

        return device_data

    def get_device_check(self):
        alert_data = {}
        device_module_status = []
        alert_code = 20000

        net_check_res = self.check.net_check()
        gps_check_res = self.check.gps_check()
        sensor_check_res = self.check.sensor_check()

        if net_check_res == (3, 1):
            self.net_enable = True
        else:
            self.net_enable = False
            device_module_status.append('net_error')

        if not gps_check_res:
            device_module_status.append('gps_error')

        if not sensor_check_res:
            # TODO: Need To Check What Sensor Error To Report.
            pass

        if device_module_status:
            self.running_led.period = 0.5
        else:
            self.running_led.period = 2

        alert_info = {'device_module_status': {i: 1 if i in device_module_status else 0 for i in settings.DEVICE_MODULE_STATUS.keys()}}
        if device_module_status:
            alert_data = self.get_alert_data(alert_code, {'local_time': self.get_local_time()})
        alert_data.update(alert_info)

        return alert_data

    def get_over_speed_check(self):
        alert_data = {}
        current_settings = settings.settings.get()
        if current_settings['app']['work_mode'] == settings.default_values_app._work_mode.intelligent:
            if self.locator.gps:
                speed = self.locator.gps.read_location_GxVTG_speed()
                if speed and float(speed) >= current_settings['app']['over_speed_threshold']:
                    alert_code = 30003
                    alert_info = {'local_time': self.get_local_time()}
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
        log.debug('[x] recive res topic [%s]' % topic)
        sys_bus.unsubscribe(topic)

        if topic.endswith('/wakelock_unlock'):
            pm.wakelock_unlock(self.power_manage.lpm_fd)
        elif topic.endswith('/power_down'):
            self.energy_led.period = None
            self.energy_led.switch(0)
            self.running_led.period = None
            self.running_led.switch(0)
            Power.powerDown()
        elif topic.endswith('/power_restart'):
            Power.powerRestart()

        if self.power_manage.callback:
            self.power_manage.callback()

        if topic.endswith('/wakelock_unlock'):
            self.power_manage.start_rtc()

    def device_data_report(self, power_switch=True, event_data={}, msg=''):
        device_data = self.get_device_data(power_switch)
        if event_data:
            device_data.update(event_data)

        num = self.get_num()
        topic = num + '/' + msg if msg else num
        sys_bus.subscribe(topic, self.data_report_cb)
        log.debug('[x] post data topic [%s]' % topic)
        self.remote.post_data(topic, device_data)

        # OTA Status RST
        current_settings = settings.settings.get()
        if current_settings['sys']['ota_status'] in (3, 4):
            settings.settings.set('ota_status', 0)
            settings.settings.save()

    def device_check(self):
        device_check_res = self.get_device_check()
        self.device_data_report(event_data=device_check_res)

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
            self.net_enable = False
            if net_check_res[0] == 1 and net_check_res[1] != 1:
                log.warn('SIM abnormal!')
                alert_code = 30004
                alert_info = {'local_time': self.get_local_time()}
                alert_data = self.get_alert_data(alert_code, alert_info)
                self.device_data_report(event_data=alert_data, msg='sim_abnormal')
        else:
            if net_check_res == (3, 1):
                self.net_enable = True


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
