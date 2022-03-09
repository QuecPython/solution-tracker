
import _thread
from queue import Queue
from usr import settings
from usr.logging import getLogger
from usr.common import Singleton

log = getLogger(__name__)


ALERTCODE = {
    30001: 'fault_alert',
    30002: 'low_power_alert',
    30003: 'over_speed_alert',
    30004: 'sim_out_alert',
    30005: 'disassemble_alert',
    40000: 'drive_behavior_alert',
    50001: 'sos_alert',
}

DRIVE_BEHAVIOR_CODE = {
    40001: 'quick_start',
    40002: 'quick_stop',
    40003: 'quick_turn_left',
    40004: 'quick_turn_right',
}


class AlertMonitorError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def alert_process(argv):
    '''
    alert_signals_queue data format

    (30001, {'local_time': 1646731286})

    (40000, {'drive_behavior_code': 40001, 'local_time': 1646731286})
    '''
    self = argv
    while True:
        data = self.alert_signals_queue.get()
        if data:
            log.info('alert_signals_queue data: ', data)
            if ALERTCODE.get(data[0]):
                current_settings = settings.settings.get()
                alert_status = current_settings.get('app', {}).get('sw_' + ALERTCODE.get(data[0]))
                if alert_status:
                    self.read_cb(ALERTCODE.get(data[0]), data[1])
                else:
                    log.warn('%s status is %s' % (ALERTCODE.get(data[0]), alert_status))
            else:
                log.error('altercode (%s) is not exists. alert info: %s' % data)


class AlertMonitor(Singleton):
    '''
    Recv alert signals and process them
    '''
    def __init__(self, alert_cb):
        self.alert_cb = alert_cb
        self.alert_signals_queue = Queue(maxsize=64)
        _thread.start_new_thread(alert_process, (self,))

    def post_alert(self, alert_code, alert_info):
        self.alert_signals_queue.put((alert_code, alert_info))
