
import _thread
from queue import Queue
from usr import settings
from usr.logging import getLogger

log = getLogger(__name__)

ALERTCODE = {
    30001: 'fault_alert',
    30002: 'low_power_alert',
    30004: 'sim_out_alert',
    30005: 'disassemble_alert',
    # 30006: 'shock_alert',  # TODO: NOT USED
    40000: 'drive_behavior_alert',
    50001: 'sos_alert',
}

DRIVEBEHAVIORCODE = {
    1: 'quick_start',
    2: 'quick_stop',
    3: 'quick_turn_left',
    4: 'quick_turn_right',
}


class AlertMonitorError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def alert_process(argv):
    '''
    alert_signals_queue data format

    (300001, {})

    (400000, {40001: True})
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


class AlertMonitor(object):
    '''
    Recv alert signals and process them
    '''
    def __init__(self, read_cb):
        self.read_cb = read_cb
        self.alert_signals_queue = Queue(maxsize=64)
        _thread.start_new_thread(alert_process, (self,))

    def post_alert(self, alert_code, alert_info):
        self.alert_signals_queue.put((alert_code, alert_info))
