import utime
import quecIot
# from queue import Queue
from usr.logging import getLogger

DATA_NON_LOCA = 0x0
DATA_LOCA_NON_GPS = 0x1
DATA_LOCA_GPS = 0x2

log = getLogger(__name__)

object_model = [
    (9,  ('power_switch', 'rw')),
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
    (20, ('disassemble_alert', 'rw')),
    (33, ('power_restart', 'w')),
    (34, ('over_speed_threshold', 'rw')),
    (35, ('over_speed_alert', 'rw')),
    (36, ('fault_code', 'r')),
    (37, ('gps_mode', 'r')),
    (38, ('user_ota_action', 'w')),
    (39, ('ota_status', 'r')),
]

object_model_code = {i[1][0]: i[0] for i in object_model}


class QuecThing(object):
    def __init__(self, pk, ps, dk, ds, downlink_queue):
        self.downlink_queue = downlink_queue
        # self.post_result_wait_queue = Queue(maxsize=16)
        self.post_result = []

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

    def get_post_result(self):
        res = True
        count = 0
        while count < 10:
            if self.post_result:
                res = self.post_result.pop()
                break
            count += 1
            utime.sleep(1)

        return res

    def put_post_result(self, res):
        self.post_result.append(res)

    def post_data(self, data_type, data):
        if data_type == DATA_NON_LOCA:
            for k, v in data.items():
                if object_model_code.get(k) is not None and v:
                    # Event Data Format From object_mode_code
                    if isinstance(v, dict):
                        v = {object_model_code.get(ik) if object_model_code.get(ik) else ik: iv for ik, iv in v.items()}
                    phymodelReport_res = quecIot.phymodelReport(1, {object_model_code.get(k): v})
                    if phymodelReport_res:
                        # res = self.post_result_wait_queue.get()
                        res = self.get_post_result()
                        if res:
                            v = {}
                            continue
                        else:
                            self.rm_empty_data(data)
                            return False
                    else:
                        self.rm_empty_data(data)
                        return False
            self.rm_empty_data(data)
            return True
        elif data_type == DATA_LOCA_GPS:
            locReportOutside_res = quecIot.locReportOutside(data)
            if locReportOutside_res:
                # return self.post_result_wait_queue.get()
                return self.get_post_result()
            else:
                return False
        elif data_type == DATA_LOCA_NON_GPS:
            locReportInside_res = quecIot.locReportInside(data)
            if locReportInside_res:
                # return self.post_result_wait_queue.get()
                return self.get_post_result()
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
                log.error('Device has been authenticated (connect failed).')
        elif event == 2:
            if errcode == 10200:
                log.info('Access succeeded.')
            if errcode == 10450:
                log.error('Device internal error (connect failed).')
        elif event == 3:
            if errcode == 10200:
                log.info('Subscription succeeded.')
        elif event == 4:
            if errcode == 10200:
                log.info('Data sending succeeded.')
                # self.post_result_wait_queue.put(True)
                self.put_post_result(True)
            elif errcode == 10210:
                log.info('Object model data sending succeeded.')
                # self.post_result_wait_queue.put(True)
                self.put_post_result(True)
            elif errcode == 10220:
                log.info('Location data sending succeeded.')
                # self.post_result_wait_queue.put(True)
                self.put_post_result(True)
            elif errcode == 10300:
                log.info('Data sending failed.')
                # self.post_result_wait_queue.put(False)
                self.put_post_result(False)
            elif errcode == 10310:
                log.error('Object model data sending failed.')
                # self.post_result_wait_queue.put(False)
                self.put_post_result(False)
            elif errcode == 10320:
                log.error('Location data sending failed.')
                # self.post_result_wait_queue.put(False)
                self.put_post_result(False)
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
                self.downlink_queue(('ota_plain', data))
                self.downlink_queue(('object_model', ('ota_status', 1)))
            elif errcode == 10701:
                log.info('The module starts to download.')
                self.downlink_queue(('object_model', ('ota_status', 2)))
            elif errcode == 10702:
                log.info('Package download.')
                self.downlink_queue(('object_model', ('ota_status', 2)))
            elif errcode == 10703:
                log.info('Package download complete.')
                self.downlink_queue(('object_model', ('ota_status', 2)))
            elif errcode == 10704:
                log.info('Package updating.')
                self.downlink_queue(('object_model', ('ota_status', 2)))
            elif errcode == 10705:
                log.info('Firmware update complete.')
                self.downlink_queue(('object_model', ('ota_status', 3)))
            elif errcode == 10706:
                log.info('Failed to update firmware.')
                self.downlink_queue(('object_model', ('ota_status', 4)))

    def dev_info_report(self):
        quecIot.devInfoReport([i for i in range(1, 13)])

    def ota_action(self, val=1):
        quecIot.otaAction(val)
