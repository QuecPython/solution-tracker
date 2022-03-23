import pm
import utime
import modem
import _thread

from queue import Queue
from machine import RTC

from usr.common import Singleton
from usr.logging import getLogger
from usr.settings import settings
from usr.settings import LOWENERGYMAP
from usr.settings import SettingsError
from usr.settings import default_values_app

try:
    from misc import USB
except ImportError:
    USB = None

log = getLogger(__name__)


class PowerManage(Singleton):

    def __init__(self, tracker, callback=None):
        self.tracker = tracker
        self.callback = callback

        self.lpm_fd = None
        self.low_energy_queue = Queue(maxsize=8)

        self.period = None
        self.low_energy_method = None
        self.set_period()
        self.get_low_energy_method()
        self.low_energy_init()

        self.rtc = RTC()
        self.rtc.register_callback(self.rtc_callback)

    def set_period(self, seconds=None):
        if seconds is None:
            current_settings = settings.get()
            seconds = current_settings['app']['work_cycle_period']
        self.period = seconds

    def start_rtc(self):
        log.debug('start PowerManage start_rtc')
        current_settings = settings.get()
        if current_settings['app']['work_mode'] == default_values_app._work_mode.intelligent:
            if self.tracker.locator.gps:
                gps_data = self.tracker.locator.gps.read()
                speed = self.tracker.locator.gps.read_location_GxVTG_speed(gps_data)
                if not speed:
                    return
                elif float(speed) <= 0:
                    return

        self.set_period()
        atime = utime.localtime(utime.mktime(utime.localtime()) + self.period)
        alarm_time = [atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0]
        self.rtc.set_alarm(alarm_time)
        log.debug('rtc set_alarm')
        self.rtc.enable_alarm(1)

    def rtc_callback(self, args):
        log.debug('start rtc_callback')
        self.rtc.enable_alarm(0)
        if self.low_energy_method == 'PM':
            self.low_energy_queue.put('wakelock_unlock')
        elif self.low_energy_method == 'PSM':
            pass
        elif self.low_energy_method == 'POWERDOWN':
            self.low_energy_queue.put('power_dwon')

    def get_low_energy_method(self):
        device_model = modem.getDevModel()
        support_methds = LOWENERGYMAP.get(device_model)
        if not support_methds:
            raise SettingsError('This Model %s Not Set LOWENERGYMAP.' % device_model)

        if self.period >= 3600:
            if "POWERDOWN" in support_methds:
                self.low_energy_method = "POWERDOWN"
            elif "PSM" in support_methds:
                self.low_energy_method = "PSM"
            elif "PM" in support_methds:
                self.low_energy_method = "PM"
        elif 60 <= self.period < 3600:
            if "PSM" in support_methds:
                self.low_energy_method = "PSM"
            elif "PM" in support_methds:
                self.low_energy_method = "PM"
        elif self.period < 60:
            if "PM" in support_methds:
                self.low_energy_method = "PM"

        return self.low_energy_method

    def low_energy_init(self):
        if self.low_energy_method == 'POWERDOWN':
            pass
        elif self.low_energy_method == 'PM':
            _thread.start_new_thread(self.low_energy_work, ())
            self.lpm_fd = pm.create_wakelock("tracker_lock", len("tracker_lock"))
            pm.autosleep(1)
        elif self.low_energy_method == 'PSM':
            # TODO: PSM LOW ENERGY
            pass

    def low_energy_work(self):
        while True:
            data = self.low_energy_queue.get()
            if data:
                if self.lpm_fd is None:
                    self.lpm_fd = pm.create_wakelock("tracker_lock", len("tracker_lock"))
                    pm.autosleep(1)
                pm.wakelock_lock(self.lpm_fd)

                over_speed_check_res = self.tracker.get_over_speed_check()
                self.tracker.device_data_report(event_data=over_speed_check_res, msg=data)
