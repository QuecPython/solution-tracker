
import quecIot
from queue import Queue
from usr.logging import getLogger

DATA_NON_LOCA = 0x0
DATA_LOCA_NON_GPS = 0x1
DATA_LOCA_GPS = 0x2

log = getLogger(__name__)

object_model = [
    (9,  'switch'),
    (4,  'energy'),
    (23, 'phone_num'),
    (24, 'loc_method'),
    (25, 'loc_mode'),
    (26, 'loc_cycle_period'),
    (19, 'local_time'),
    (15, 'low_power_alert_threshold'),
    (16, 'low_power_shutdown_threshold'),
    (12, 'sw_ota'),
    (13, 'sw_ota_auto_upgrade'),
    (10, 'sw_voice_listen'),
    (11, 'sw_voice_record'),
    (27, 'sw_fault_alert'),
    (28, 'sw_low_power_alert'),
    (29, 'sw_over_speed_alert'),
    (30, 'sw_sim_out_alert'),
    (31, 'sw_disassemble_alert'),
    (32, 'sw_drive_behavior_alert'),
    (21, 'drive_behavior_code'),
    (6,  'sos_alert'),
    (14, 'fault_alert'),
    (17, 'low_power_alert'),
    (18, 'sim_out_alert'),
    (22, 'drive_behavior_alert'),
    (20, 'disassemble_alert')
]

class QuecThing(object):
    def __init__(self, pk, ps, dk, ds, downlink_queue):
        self.downlink_queue = downlink_queue
        self.post_result_wait_queue = Queue(maxsize=16)
        quecIot.init()
        quecIot.setEventCB(self.eventCB)
        quecIot.setProductinfo(pk, ps)
        quecIot.setDkDs(dk, ds)
        quecIot.setServer(1, "iot-south.quectel.com:2883")
        quecIot.setConnmode(1)

    @staticmethod
    def rm_empty_data(data):
        for k, v in data.items():
            if not v:
                del data[k]

    def post_data(self, data_type, data):
        if data_type == DATA_NON_LOCA:
            for k, v in data.items():
                for om in object_model:
                    if k == om[1]:
                        if v:
                            if quecIot.phymodelReport(1, {om[0]: v}):
                                res = self.post_result_wait_queue.get()
                                if res:
                                    v = {}
                                    continue
                                else:
                                    self.rm_empty_data(data)
                                    return False
                            else:
                                self.rm_empty_data(data)
                                return False
                        else:
                            continue
            self.rm_empty_data(data)
            return True
        elif data_type == DATA_LOCA_GPS:
            if quecIot.locReportOutside(data):
                return self.post_result_wait_queue.get()
            else:
                return False
        elif data_type == DATA_LOCA_NON_GPS:
            if quecIot.locReportInside(data):
                return self.post_result_wait_queue.get()
            else:
                return False
        else:
            return False
            # raise ValueError('No such locator (0x%X).' % data_type)

    def eventCB(self, data):
        log.info("event:", data)
        event = data[0]
        errcode = data[1]
        if len(data) > 2:
            data = data[2]

        if event == 1:
            if errcode == 10200:
                log.info('Device authentication succeeded.')
            elif errcode == 10422:
                log.info('Device has been authenticated (connect failed).')
        elif event == 2:
            if errcode == 10200:
                log.info('Access succeeded.')
        elif event == 3:
            if errcode == 10200:
                log.info('Subscription succeeded.')
        elif event == 4:
            if errcode == 10200:
                log.info('Data sending succeeded.')
                self.post_result_wait_queue.put(True)
            elif errcode == 10210:
                log.info('Object model data sending succeeded.')
                self.post_result_wait_queue.put(True)
            elif errcode == 10220:
                log.info('Location data sending succeeded.')
                self.post_result_wait_queue.put(True)
            elif errcode == 10300:
                log.info('Data sending failed.')
                self.post_result_wait_queue.put(False)
            elif errcode == 10310:
                log.info('Object model data sending failed.')
                self.post_result_wait_queue.put(False)
            elif errcode == 10320:
                log.info('Location data sending failed.')
                self.post_result_wait_queue.put(False)
        elif event == 5:
            if errcode == 10200:
                log.info('Recving raw data.')
                log.info(data)
                '''
                self.downlink_queue.put(data)
                '''
            if errcode == 10210:
                log.info('Recving object model data.')
                '''
                self.downlink_queue.put(data)
                '''
            elif errcode == 10211:
                log.info('Recving object model query command.')
        elif event == 6:
            if errcode == 10200:
                log.info('Logout succeeded.')
        elif event == 7:
            if errcode == 10700:
                log.info('New OTA plain.')
