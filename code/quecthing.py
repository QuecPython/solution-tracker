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

import utime
import osTimer
import quecIot

# from misc import Power
from queue import Queue

from usr.logging import getLogger
from usr.settings import settings

log = getLogger(__name__)

object_model = [
    # property
    (9,  ('power_switch', 'rw')),
    (4,  ('energy', 'r')),
    (23, ('phone_num', 'rw')),
    (24, ('loc_method', 'rw')),
    (25, ('work_mode', 'rw')),
    (26, ('work_cycle_period', 'rw')),
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
    (30, ('sw_sim_abnormal_alert', 'rw')),
    (31, ('sw_disassemble_alert', 'rw')),
    (32, ('sw_drive_behavior_alert', 'rw')),
    (21, ('drive_behavior_code', 'r')),
    (33, ('power_restart', 'w')),
    (34, ('over_speed_threshold', 'rw')),
    (36, ('device_module_status', 'r')),
    (37, ('gps_mode', 'r')),
    (38, ('user_ota_action', 'w')),
    (39, ('ota_status', 'r')),
    (41, ('voltage', 'r')),

    # event
    (6,  ('sos_alert', 'r')),
    (14, ('fault_alert', 'r')),
    (17, ('low_power_alert', 'r')),
    (18, ('sim_abnormal_alert', 'r')),
    (20, ('disassemble_alert', 'r')),
    (22, ('drive_behavior_alert', 'r')),
    (35, ('over_speed_alert', 'r')),
]

object_model_struct = {
    'device_module_status': {
        'net': 1,
        'location': 2,
        'temp_sensor': 3,
        'light_sensor': 4,
        'move_sensor': 5,
        'mike': 6,
    },
    'loc_method': {
        'gps': 1,
        'cell': 2,
        'wifi': 3,
    }
}

object_model_code = {i[1][0]: i[0] for i in object_model}


class QuecThing(object):
    def __init__(self, pk, ps, dk, ds, downlink_queue):
        self.downlink_queue = downlink_queue
        self.post_result_wait_queue = Queue(maxsize=16)
        self.quec_timer = osTimer()
        self.queciot_init(pk, ps, dk, ds)

    def queciot_init(self, pk, ps, dk, ds):
        quecIot.init()
        quecIot.setEventCB(self.eventCB)
        quecIot.setProductinfo(pk, ps)
        quecIot.setDkDs(dk, ds)
        quecIot.setServer(1, "iot-south.quectel.com:2883")
        quecIot.setConnmode(1)
        if not ds and dk:
            count = 0
            while count < 3:
                ndk, nds = quecIot.getDkDs()
                if nds:
                    break
                count += 1
                utime.sleep(count)
            current_settings = settings.get()
            cloud_init_params = current_settings['sys']['cloud_init_params']
            cloud_init_params['DS'] = nds
            settings.set('cloud_init_params', cloud_init_params)
            settings.save()

    def get_post_res(self):
        current_settings = settings.get()
        self.quec_timer.start(current_settings['sys']['checknet_timeout'] * 1000, 1, self.quec_timer_cb)
        res = self.post_result_wait_queue.get()
        self.quec_timer.stop()
        return res

    def quec_timer_cb(self, args):
        # Power.powerRestart()
        self.post_result_wait_queue.put(False)

    @staticmethod
    def rm_empty_data(data):
        for k, v in data.items():
            if not v:
                del data[k]

    def post_data(self, data):
        res = True
        # log.debug('post_data: %s' % str(data))
        for k, v in data.items():
            if object_model_code.get(k) is not None:
                # Event Data Format From object_mode_code
                if v is not None:
                    if isinstance(v, dict):
                        nv = {}
                        for ik, iv in v.items():
                            if object_model_code.get(ik):
                                nv[object_model_code.get(ik)] = iv
                            else:
                                if object_model_struct.get(k):
                                    nv[object_model_struct[k].get(ik)] = iv
                                else:
                                    nv[ik] = iv
                        v = nv
                    # log.debug('k: %s, v: %s' % (k, v))
                    phymodelReport_res = quecIot.phymodelReport(1, {object_model_code.get(k): v})
                    if not phymodelReport_res:
                        res = False
                        break
                else:
                    continue
            elif k == 'gps':
                locReportOutside_res = quecIot.locReportOutside(v)
                if not locReportOutside_res:
                    res = False
                    break
            elif k == 'non_gps':
                locReportInside_res = quecIot.locReportInside(v)
                if not locReportInside_res:
                    res = False
                    break
            else:
                v = {}
                continue

            res = self.get_post_res()
            if res:
                v = {}
            else:
                res = False
                break

        self.rm_empty_data(data)
        return res

    def eventCB(self, data):
        log.info("event: %s" % str(data))
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
                log.error('Object model data sending failed.')
                self.post_result_wait_queue.put(False)
            elif errcode == 10320:
                log.error('Location data sending failed.')
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
                self.downlink_queue.put(('ota_plain', data))
                self.downlink_queue.put(('object_model', [('ota_status', 1)]))
            elif errcode == 10701:
                log.info('The module starts to download.')
                self.downlink_queue.put(('object_model', [('ota_status', 2)]))
            elif errcode == 10702:
                log.info('Package download.')
                self.downlink_queue.put(('object_model', [('ota_status', 2)]))
            elif errcode == 10703:
                log.info('Package download complete.')
                self.downlink_queue.put(('object_model', [('ota_status', 2)]))
            elif errcode == 10704:
                log.info('Package updating.')
                self.downlink_queue.put(('object_model', [('ota_status', 2)]))
            elif errcode == 10705:
                log.info('Firmware update complete.')
                self.downlink_queue.put(('object_model', [('ota_status', 3)]))
            elif errcode == 10706:
                log.info('Failed to update firmware.')
                self.downlink_queue.put(('object_model', [('ota_status', 4)]))

    def dev_info_report(self):
        quecIot.devInfoReport([i for i in range(1, 13)])

    def ota_action(self, val=1):
        quecIot.otaAction(val)
