
import quecIot
from queue import Queue
from usr.logging import getLogger

DATA_NON_LOCA = 0x0
DATA_LOCA_NON_GPS = 0x1
DATA_LOCA_GPS = 0x2

log = getLogger(__name__)

object_model = [
    (9,  ('switch', 'rw')),
    (4,  ('energy', 'r')),
    (23, ('phone_num', 'rw')),
    (24, ('loc_method', 'rw')),
    (25, ('loc_mode', 'rw')),
    (26, ('loc_cycle_period', 'rw')),
    (19, ('local_time', 'r')),
    (15, ('low_power_alert_threshold', 'rw')),
    (16, ('low_power_shutdown_threshold', 'rw')),
    (12, ('sw_ota', 'rw')),
    (13, ('sw_ota_auto_upgrade', 'rw')),
    (10, ('sw_voice_listen', 'rw')),
    (11, ('sw_voice_record', 'rw')),
    (27, ('sw_fault_alert', 'rw')),
    (28, ('sw_low_power_alert', 'rw')),
    (29, ('sw_over_speed_alert', 'rw')),
    (30, ('sw_sim_out_alert', 'rw')),
    (31, ('sw_disassemble_alert', 'rw')),
    (32, ('sw_drive_behavior_alert', 'rw')),
    (21, ('drive_behavior_code', 'r')),
    (6,  ('sos_alert', 'rw')),
    (14, ('fault_alert', 'rw')),
    (17, ('low_power_alert', 'rw')),
    (18, ('sim_out_alert', 'rw')),
    (22, ('drive_behavior_alert', 'rw')),
    (20, ('disassemble_alert', 'rw'))
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
                # TODO: To Check data format.
                self.downlink_queue.put(('raw_data', data))
            if errcode == 10210:
                log.info('Recving object model data.')
                dl_data = [(dict(object_model)[k][0], v.decode() if isinstance(v, bytes) else v) for k, v in data.items() if 'w' in dict(object_model)[k][1]]
                self.downlink_queue.put(('object_model', dl_data))
            elif errcode == 10211:
                log.info('Recving object model query command.')
                # TODO: Check pkgId for other uses.
                # log.info('pkgId: %s' % data[0])
                object_model_ids = data[1]
                object_model_val = [dict(object_model)[i][0] for i in object_model_ids if dict(object_model).get(i) is not None and 'r' in dict(object_model)[i][1]]
                self.downlink_queue.put(('query', object_model_val))
        elif event == 6:
            if errcode == 10200:
                log.info('Logout succeeded.')
        elif event == 7:
            if errcode == 10700:
                log.info('New OTA plain.')
