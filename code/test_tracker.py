import ure
import utime

import usr.settings as settings
from machine import UART

from queue import Queue
from usr.logging import getLogger
from usr.quecthing import QuecThing
from usr.remote import Remote
# from usr.location import Location
from usr.tracker import Tracker

log = getLogger(__name__)


def test_quecthing():
    log.info('[x] start test_quecthing')
    current_settings = settings.settings.get()
    cloud_init_params = current_settings['sys']['cloud_init_params']
    downlink_queue = Queue(maxsize=64)
    cloud = QuecThing(cloud_init_params['PK'], cloud_init_params['PS'], cloud_init_params['DK'], cloud_init_params['DS'], downlink_queue)
    cloud.post_data(0x0, 'put test msg.')
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

    log.info('[.] sleep 10')
    utime.sleep(10)

    log.debug('[x] start to machine check.')
    tracker.machine_check()
    log.debug('[x] end to machine check.')

    log.info('[.] sleep 10')
    utime.sleep(10)

    # log.debug('[.] set loc_mode 0x0.')
    # settings.settings.set('loc_mode', 0x0)
    # settings.settings.save()
    # log.debug('[.] tracker_command_queue put loc_mode.')
    # tracker.tracker_command_queue.put('loc_mode')

    # log.info('[.] sleep 10')
    # utime.sleep(10)

    # log.debug('[.] set loc_mode 0x1.')
    # settings.settings.set('loc_mode', 0x1)
    # settings.settings.save()
    # log.debug('[.] tracker_command_queue put loc_mode.')
    # tracker.tracker_command_queue.put('loc_mode')

    # log.info('[.] sleep 5')
    # utime.sleep(5)

    # log.info('[.] locator trigger')
    # tracker.locator.trigger()
    # log.info('[.] sleep 3')
    # utime.sleep(3)
    # log.info('[.] alert post_alert')
    # tracker.alert.post_alert(40000, {'drive_behavior_code': 40001, 'local_time': utime.mktime(utime.localtime())})

    log.info('[x] end test_tracker')


def main():
    # test_quecthing()
    # test_settings()
    # test_uart()
    # test_remote()
    test_tracker()

if __name__ == '__main__':
    main()
