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

from queue import Queue

from usr.logging import getLogger
from usr.settings import settings
from usr.settings import PROJECT_NAME
from usr.settings import PROJECT_VERSION
from usr.ota import SotaDownloadUpgrade
from usr.ota import OTAFileClear

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
    (41, ('voltage', 'r')),
    (42, ('ota_status', 'r')),
    (43, ('current_speed', 'r')),

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
    },
    'ota_status': {
        'sys_current_version': 1,
        'sys_target_version': 2,
        'app_current_version': 3,
        'app_target_version': 4,
        'upgrade_module': 5,
        'upgrade_status': 6,
    },
}

object_model_code = {i[1][0]: i[0] for i in object_model}


class QuecThing(object):
    def __init__(self, pk, ps, dk, ds, server, downlink_queue):
        self.pk = pk
        self.ps = ps
        self.dk = dk
        self.ds = ds
        self.server = server
        self.fileSize = 0
        self.needDownloadSize = 0
        self.crcValue = 0
        self.downloadSize = 0
        self.fileFp = 0
        self.startAddr = 0
        self.downlink_queue = downlink_queue
        self.post_result_wait_queue = Queue(maxsize=16)
        self.quec_timer = osTimer()
        self.cloud_init()

        fileClear = OTAFileClear()
        fileClear.file_clear()

    def cloud_init(self, enforce=False):
        current_settings = settings.get()
        log.debug(
            '[cloud_init start] enforce: %s QuecThing Work State: %s, quecIot.getConnmode(): %s'
            % (enforce, quecIot.getWorkState(), quecIot.getConnmode())
        )
        if enforce is False:
            if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
                return True

        quecIot.init()
        quecIot.setEventCB(self.eventCB)
        quecIot.setProductinfo(self.pk, self.ps)
        if self.dk or self.ds:
            quecIot.setDkDs(self.dk, self.ds)
        quecIot.setServer(1, self.server)
        quecIot.setLifetime(current_settings['sys']['cloud_life_time'])
        quecIot.setMcuVersion(PROJECT_NAME, PROJECT_VERSION)
        quecIot.setConnmode(1)

        count = 0
        while quecIot.getWorkState() != 8 and count < 10:
            utime.sleep_ms(200)
            count += 1

        if not self.ds and self.dk:
            count = 0
            while count < 3:
                dkds = quecIot.getDkDs()
                if dkds:
                    self.dk, self.ds = dkds
                    break
                count += 1
                utime.sleep(count)
            cloud_init_params = current_settings['sys']['cloud_init_params']
            cloud_init_params['DS'] = self.ds
            settings.set('cloud_init_params', cloud_init_params)
            settings.save()

        log.debug('[cloud_init over] QuecThing Work State: %s, quecIot.getConnmode(): %s' % (quecIot.getWorkState(), quecIot.getConnmode()))
        if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
            return True
        else:
            return False

    def get_post_res(self):
        self.quec_timer.start(5000, 0, self.quec_timer_cb)
        res = self.post_result_wait_queue.get()
        self.quec_timer.stop()
        return res

    def quec_timer_cb(self, args):
        self.post_result_wait_queue.put(False)
        self.quec_timer.stop()

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
                self.ota_request()
                if data != (3, 10200):
                    ota_info = data.decode()
                    file_info = ota_info.split(',')
                    log.info(
                        "OTA File Info: componentNo: %s, sourceVersion: %s, targetVersion: %s, "
                        "batteryLimit: %s, minSignalIntensity: %s, minSignalIntensity: %s" % tuple(file_info)
                    )
            if errcode == 10300:
                log.info('Subscription failed.')
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
                ota_info = data.decode()
                file_info = ota_info.split(',')
                log.info(
                    "OTA File Info: componentNo: %s, sourceVersion: %s, targetVersion: %s, "
                    "batteryLimit: %s, minSignalIntensity: %s, useSpace: %s" % tuple(file_info)
                )
                self.downlink_queue.put(('object_model', [('ota_status', (data[0], 1, data[2]))]))
                self.downlink_queue.put(('ota_plain', data))
            elif errcode == 10701:
                log.info('The module starts to download.')
                if data != (7, 10701):
                    ota_info = data.decode()
                    file_info = ota_info.split(',')
                    self.sota_download_info(int(file_info[1]), file_info[2], int(file_info[3]))
                self.downlink_queue.put(('object_model', [('ota_status', (None, 2, None))]))
            elif errcode == 10702:
                log.info('Package download.')
                self.downlink_queue.put(('object_model', [('ota_status', (None, 2, None))]))
            elif errcode == 10703:
                log.info('Package download complete.')
                if data != (7, 10703):
                    ota_info = data.decode()
                    file_info = ota_info.split(',')
                    log.info("OTA File Info: componentNo: %s, length: %s, md5: %s, crc: %s" % tuple(file_info))
                    self.sota_download_success(int(file_info[2]), int(file_info[3]))
                self.downlink_queue.put(('object_model', [('ota_status', (None, 2, None))]))
            elif errcode == 10704:
                log.info('Package updating.')
                self.downlink_queue.put(('object_model', [('ota_status', (None, 2, None))]))
            elif errcode == 10705:
                log.info('Firmware update complete.')
                self.downlink_queue.put(('object_model', [('ota_status', (None, 3, None))]))
            elif errcode == 10706:
                log.info('Failed to update firmware.')
                self.downlink_queue.put(('object_model', [('ota_status', (None, 4, None))]))
            elif errcode == 10707:
                log.info('Received confirmation broadcast.')

    def ota_request(self):
        quecIot.otaRequest(0)

    def ota_action(self, val=1):
        quecIot.otaAction(val)

    def sota_download_info(self, size, md5_value, crc):
        self.file_size = size
        self.crc_value = crc
        self.download_size = 0
        self.update_mode = SotaDownloadUpgrade()
        self.md5_value = md5_value

    def sota_download_success(self, start, down_loaded_size):
        self.need_download_size = down_loaded_size
        self.start_addr = start
        self.read_sota_file()

    def read_sota_file(self):
        while self.need_download_size != 0:
            readsize = 4096
            if (readsize > self.need_download_size):
                readsize = self.need_download_size
            updateFile = quecIot.mcuFWDataRead(self.start_addr, readsize)
            self.update_mode.write_update_data(updateFile)
            log.debug("Download File Size: %s" % readsize)
            self.need_download_size -= readsize
            self.start_addr += readsize
            self.download_size += readsize
            if (self.download_size == self.file_size):
                log.debug("File Download Success, Update Start.")
                quecIot.otaAction(3)
                file_update_res = self.update_mode.file_update(self.md5_value)
                if file_update_res:
                    self.update_mode.sota_set_flag()
                    log.debug("File Update Success, Power Restart.")
                else:
                    log.debug("File Update Failed.")
                self.downlink_queue.put(('object_model', [('power_restart', 1)]))
            else:
                quecIot.otaAction(2)
