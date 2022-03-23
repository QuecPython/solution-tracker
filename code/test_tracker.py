import pm
import ure
import utime
import _thread

from queue import Queue
from machine import RTC
from machine import UART
# from misc import Power

import usr.settings as settings

from usr.logging import getLogger
from usr.quecthing import QuecThing
from usr.remote import Remote
from usr.location import Location, GPS
from usr.tracker import Tracker
from usr.aliyunIot import AliYunIot

log = getLogger(__name__)


class QuecIotLog(object):
    def __init__(self):
        self.cfg = settings.default_values_sys._gps_cfg
        self.quecIot_log_queue = Queue(maxsize=16)
        self.uart_obj = UART(
            UART.UART0, self.cfg['buadrate'], self.cfg['databits'],
            self.cfg['parity'], self.cfg['stopbits'], self.cfg['flowctl']
        )
        self.uart_obj.set_callback(self.quecIot_log_retrieve_cb)
        _thread.start_new_thread(self.quecIot_log_retrieve_thread, ())

    def quecIot_log_retrieve_cb(self, params):
        log.debug('[quecIot_log] %s' % params)

    def quecIot_log_retrieve_thread(self):
        while True:
            data = self.uart_obj.read()
            log.info('[quecIot_log] UART0 Read Data:', data)
            utime.sleep(3)

    def uart_send_data(self):
        self.uart_obj.write('test usrt0 log.')


def test_quecthing():
    log.info('[x] start test_quecthing')
    current_settings = settings.settings.get()
    cloud_init_params = current_settings['sys']['cloud_init_params']
    downlink_queue = Queue(maxsize=64)
    cloud = QuecThing(cloud_init_params['PK'], cloud_init_params['PS'], cloud_init_params['DK'], cloud_init_params['DS'], downlink_queue)
    post_data_res = cloud.post_data({'power_switch': True})
    log.info('post_data_res:', post_data_res)
    log.info('[x] end test_quecthing')


def test_settings():
    log.info('[x] start test_settings')
    current_settings = settings.settings.get()
    log.info("current_settings", current_settings)
    settings.Settings().reset()
    current_settings = settings.settings.get()
    log.info("current_settings", current_settings)
    log.info('[x] end test_settings')


def test_uart():
    log.info('[x] start test_uart')
    current_settings = settings.settings.get()
    gps_cfg = current_settings['sys']['locator_init_params']

    uart1 = UART(UART.UART1, gps_cfg['buadrate'], gps_cfg['databits'], gps_cfg['parity'], gps_cfg['stopbits'], gps_cfg['flowctl'])
    log.info("uart1.write('Test UART1 Msg.')")
    uart1.write('Test UART1 Msg.')
    utime.sleep(1)
    ms = uart1.any()
    log.info("uart1.any()", ms)
    if ms:
        msg = uart1.read(ms)
        log.info("uart1 read msg", msg)
    uart1.close()


def test_ure():
    gps_data = '$GNVTG,218.45,T,,M,0.03,N,0.06,K,A*2C'
    a = ure.search(r',N,[0-9]+\.[0-9]+,K,', gps_data)
    if a:
        print(a.group[0])


def test_remote():
    log.info('[x] start test_remote')
    log.info('settings.current_settings: %s' % settings.settings.get())
    Remote()
    log.info('[x] end test_remote')


def test_tracker():
    log.info('[x] start test_tracker')

    tracker = Tracker()

    log.info('[.] sleep 3')
    utime.sleep(3)

    # log.info('[.] test tracker.device_data_report()')
    # device_data_report_res = tracker.device_data_report()
    # log.info('[.] device_data_report_res:', device_data_report_res)

    # log.info('[.] sleep 3')
    # utime.sleep(3)

    log.info('[.] test tracker.power_manage.start_rtc()')
    tracker.power_manage.start_rtc()
    log.info('[.] end tracker.power_manage.start_rtc()')

    # log.info('[.] test tracker.device_check()')
    # device_check_res = tracker.device_check()
    # log.info('[.] device_check_res:', device_check_res)

    # log.info('[.] test tracker.remote.check_ota()')
    # tracker.remote.check_ota()

    # log.info('[.] sleep 3')
    # utime.sleep(3)

    # log.info('[.] test tracker.machine_check()')
    # machine_check_res = tracker.machine_check()
    # log.info('[.] machine_check_res:', machine_check_res)

    log.info('[x] end test_tracker')


def test_location():
    log.debug('[x] start test_location')
    try:
        locator = Location(None)
        if locator.gps is not None:
            gps_data = None
            retry = 0
            while retry < 10:
                gps_data = locator.gps.quecgnss_read()
                if gps_data:
                    log.debug('gps_data: %s' % gps_data)
                    break
                else:
                    log.debug('gps_data is empty: %s' % gps_data)
                utime.sleep(1)
    except Exception as e:
        raise e
    log.debug('[x] end test_location')


def test_gps():
    log.debug('[x] start test_gps')
    gps = GPS(settings.default_values_sys._gps_cfg)
    gps_data = None
    retry = 0
    while retry < 10:
        gps_data = gps.quecgnss_read()
        if gps_data:
            log.debug('gps_data: %s' % gps_data)
            break
        else:
            log.debug('gps_data is empty: %s' % gps_data)
        utime.sleep(1)

    log.debug('[x] gps_data: %s' % gps_data)
    log.debug('[x] end test_gps')


def test_aliyuniot():
    log.debug('[x] start test_aliyuniot')

    current_settings = settings.settings.get()
    cloud_init_params = current_settings['sys']['cloud_init_params']
    downlink_queue = Queue(maxsize=64)
    cloud = AliYunIot(cloud_init_params['PK'], cloud_init_params['PS'], cloud_init_params['DK'], cloud_init_params['DS'], downlink_queue)
    log.debug("cloud.ali.getAliyunSta(): ", cloud.ali.getAliyunSta())

    log.debug('[x] end test_aliyuniot')


def test_pm():
    # create wakelock
    lpm_fd = pm.create_wakelock("test_lock", len("test_lock"))
    # set auto sleep
    pm.autosleep(1)

    # 模拟测试，实际开发请根据业务场景选择使用
    count = 0
    while count < 3:
        utime.sleep(20)  # 休眠
        res = pm.wakelock_lock(lpm_fd)
        print("ql_lpm_idlelock_lock, g_c1_axi_fd = %d" % lpm_fd)
        print("unlock  sleep")
        utime.sleep(20)
        res = pm.wakelock_unlock(lpm_fd)
        print(res)
        print("ql_lpm_idlelock_unlock, g_c1_axi_fd = %d" % lpm_fd)
        num = pm.get_wakelock_num()  # 获取已创建锁的数量
        print(num)
        count += 1

    pm.delete_wakelock(lpm_fd)


def test_rtc():
    rtc_queue = Queue(maxsize=8)

    def rtc_cb(df):
        global rtc_queue
        print('rtc call back test. [%s]' % df)
        rtc_queue.put('rtc')

    rtc = RTC()
    log.debug('rtc.datatime: %s' % str(rtc.datetime()))
    rtc.register_callback(rtc_cb)

    atime = utime.localtime(utime.mktime(utime.localtime()) + 10)
    alarm_time = (atime[0], atime[1], atime[2], 0, atime[3], atime[4], atime[5], 0)
    log.debug('rtc.set_alarm alarm_time: %s' % str(alarm_time))
    rtc.set_alarm(alarm_time)
    log.debug('rtc.enable_alarm')
    rtc.enable_alarm(1)
    rtc_data = rtc_queue.get()
    log.debug('rtc_data: %s' % rtc_data)

    # log.debug('Power.powerDown')
    # Power.powerDown()


def main():
    # test_quecthing()
    # test_settings()
    # test_uart()
    # test_remote()
    # test_location()
    # test_gps()
    # test_aliyuniot()
    test_tracker()
    # test_pm()
    # test_rtc()

if __name__ == '__main__':
    main()
