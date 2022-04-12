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

from usr.ota import SOTA
from usr.common import CloudObservable
from usr.logging import getLogger
from usr.location import GPSParsing

log = getLogger(__name__)

object_model = [
    # property
    (9,  ("power_switch", "rw")),
    (4,  ("energy", "r")),
    (23, ("phone_num", "rw")),
    (24, ("loc_method", "rw")),
    (25, ("work_mode", "rw")),
    (26, ("work_cycle_period", "rw")),
    (19, ("local_time", "r")),
    (15, ("low_power_alert_threshold", "rw")),
    (16, ("low_power_shutdown_threshold", "rw")),
    (12, ("sw_ota", "rw")),
    (13, ("sw_ota_auto_upgrade", "rw")),
    (10, ("sw_voice_listen", "rw")),
    (11, ("sw_voice_record", "rw")),
    (27, ("sw_fault_alert", "rw")),
    (28, ("sw_low_power_alert", "rw")),
    (29, ("sw_over_speed_alert", "rw")),
    (30, ("sw_sim_abnormal_alert", "rw")),
    (31, ("sw_disassemble_alert", "rw")),
    (32, ("sw_drive_behavior_alert", "rw")),
    (21, ("drive_behavior_code", "r")),
    (33, ("power_restart", "w")),
    (34, ("over_speed_threshold", "rw")),
    (36, ("device_module_status", "r")),
    (37, ("gps_mode", "r")),
    (38, ("user_ota_action", "w")),
    (41, ("voltage", "r")),
    (42, ("ota_status", "r")),
    (43, ("current_speed", "r")),

    # event
    (6,  ("sos_alert", "r")),
    (14, ("fault_alert", "r")),
    (17, ("low_power_alert", "r")),
    (18, ("sim_abnormal_alert", "r")),
    (20, ("disassemble_alert", "r")),
    (22, ("drive_behavior_alert", "r")),
    (35, ("over_speed_alert", "r")),
]

object_model_struct = {
    "device_module_status": {
        "net": 1,
        "location": 2,
        "temp_sensor": 3,
        "light_sensor": 4,
        "move_sensor": 5,
        "mike": 6,
    },
    "loc_method": {
        "gps": 1,
        "cell": 2,
        "wifi": 3,
    },
    "ota_status": {
        "sys_current_version": 1,
        "sys_target_version": 2,
        "app_current_version": 3,
        "app_target_version": 4,
        "upgrade_module": 5,
        "upgrade_status": 6,
    },
}

object_model_code = {i[1][0]: i[0] for i in object_model}


EVENT_CODE = {
    1: {
        10200: "Device authentication succeeded.",
        10420: "Bad request data (connection failed).",
        10422: "Device authenticated (connection failed).",
        10423: "No product information found (connection failed).",
        10424: "PAYLOAD parsing failed (connection failed).",
        10425: "Signature verification failed (connection failed).",
        10426: "Bad authentication version (connection failed).",
        10427: "Invalid hash information (connection failed).",
        10430: "PK changed (connection failed).",
        10431: "Invalid DK (connection failed).",
        10432: "PK does not match authentication version (connection failed).",
        10450: "Device internal error (connection failed).",
        10466: "Boot server address not found (connection failed).",
        10500: "Device authentication failed (an unknown exception occurred in the system).",
        10300: "Other errors.",
    },
    2: {
        10200: "Access is successful.",
        10430: "Incorrect device key (connection failed).",
        10431: "Device is disabled (connection failed).",
        10450: "Device internal error (connection failed).",
        10471: "Implementation version not supported (connection failed).",
        10473: "Abnormal access heartbeat (connection timed out).",
        10474: "Network exception (connection timed out).",
        10475: "Server changes.",
        10476: "Abnormal connection to AP.",
        10500: "Access failed (an unknown exception occurred in the system).",
    },
    3: {
        10200: "Subscription succeeded.",
        10300: "Subscription failed.",
    },
    4: {
        10200: "Transparent data sent successfully.",
        10210: "Object model data sent successfully.",
        10220: "Positioning data sent successfully.",
        10300: "Failed to send transparent data.",
        10310: "Failed to send object model data.",
        10320: "Failed to send positioning data.",
    },
    5: {
        10200: "Receive transparent data.",
        10210: "Receive data from the object model.",
        10211: "Received object model query command.",
        10473: "Received data but the length exceeds the module buffer limit, receive failed.",
        10428: "The device receives too much buffer and causes current limit.",
    },
    6: {
        10200: "Logout succeeded (disconnection succeeded).",
    },
    7: {
        10700: "New OTA plain.",
        10701: "The module starts to download.",
        10702: "Package download.",
        10703: "Package download complete.",
        10704: "Package update.",
        10705: "Firmware update complete.",
        10706: "Failed to update firmware.",
        10707: "Received confirmation broadcast.",
    },
    8: {
        10428: "High-frequency messages on the device cause current throttling.",
        10429: "Exceeds the number of activations per device or daily requests current limit.",
    }
}


class QuecThing(CloudObservable):
    def __init__(self, pk, ps, dk, ds, server, life_time=120, mcu_name="", mcu_version=""):
        super().__init__()
        self.pk = pk
        self.ps = ps
        self.dk = dk
        self.ds = ds
        self.server = server
        self.life_time = life_time
        self.mcu_name = mcu_name
        self.mcu_version = mcu_version

        self.file_size = 0
        self.md5_value = ""
        self.post_result_wait_queue = Queue(maxsize=16)
        self.quec_timer = osTimer()

    def __rm_empty_data(self, data):
        for k, v in data.items():
            if not v:
                del data[k]

    def __quec_timer_cb(self, args):
        self.__put_post_res(False)

    def __get_post_res(self):
        self.quec_timer.start(5000, 0, self.__quec_timer_cb)
        res = self.post_result_wait_queue.get()
        self.quec_timer.stop()
        return res

    def __put_post_res(self, res):
        if self.post_result_wait_queue.size() >= 16:
            self.post_result_wait_queue.get()
        self.post_result_wait_queue.put(res)

    def __sota_download_info(self, size, md5_value):
        self.file_size = size
        self.md5_value = md5_value

    def __sota_upgrade_start(self, start_addr, need_download_size):
        download_size = 0
        sota_mode = SOTA()
        while need_download_size != 0:
            readsize = 4096
            if (readsize > need_download_size):
                readsize = need_download_size
            updateFile = quecIot.mcuFWDataRead(start_addr, readsize)
            sota_mode.write_update_data(updateFile)
            log.debug("Download File Size: %s" % readsize)
            need_download_size -= readsize
            start_addr += readsize
            download_size += readsize
            if (download_size == self.file_size):
                log.debug("File Download Success, Update Start.")
                self.ota_action(3)
                if sota_mode.check_md5(self.md5_value):
                    if sota_mode.file_update():
                        sota_mode.sota_set_flag()
                        log.debug("File Update Success, Power Restart.")
                    else:
                        log.debug("File Update Failed, Power Restart.")
                break
            else:
                self.ota_action(2)

        res_data = ("object_model", [("power_restart", 1)])
        self.notifyObservers(self, *res_data)

    def __event_cb(self, data):
        res_data = ()
        event = data[0]
        errcode = data[1]
        eventdata = b""
        if len(data) > 2:
            eventdata = data[2]
        log.info("Event[%s] ErrCode[%s] Msg[%s] EventData[%s]" % (event, errcode, EVENT_CODE.get(event, {}).get(errcode, ""), eventdata))

        if event == 3:
            if errcode == 10200:
                if eventdata:
                    file_info = eval(eventdata)
                    log.info("OTA File Info: componentNo: %s, sourceVersion: %s, targetVersion: %s, "
                             "batteryLimit: %s, minSignalIntensity: %s, minSignalIntensity: %s" % file_info)
        elif event == 4:
            if errcode == 10200:
                self.__put_post_res(True)
            elif errcode == 10210:
                self.__put_post_res(True)
            elif errcode == 10220:
                self.__put_post_res(True)
            elif errcode == 10300:
                self.__put_post_res(False)
            elif errcode == 10310:
                self.__put_post_res(False)
            elif errcode == 10320:
                self.__put_post_res(False)
        elif event == 5:
            if errcode == 10200:
                # TODO: Data Type Passthrough (Not Support Now).
                res_data = ("raw_data", eventdata)
            elif errcode == 10210:
                dl_data = [(dict(object_model)[k][0], v.decode() if isinstance(v, bytes) else v) for k, v in eventdata.items() if "w" in dict(object_model)[k][1]]
                res_data = ("object_model", dl_data)
            elif errcode == 10211:
                # eventdata[0] is pkgId.
                object_model_ids = eventdata[1]
                object_model_val = [dict(object_model)[i][0] for i in object_model_ids if dict(object_model).get(i) is not None and "r" in dict(object_model)[i][1]]
                res_data = ("query", object_model_val)
                pass
        elif event == 7:
            if errcode == 10700:
                if eventdata:
                    file_info = eval(eventdata)
                    log.info("OTA File Info: componentNo: %s, sourceVersion: %s, targetVersion: %s, "
                             "batteryLimit: %s, minSignalIntensity: %s, useSpace: %s" % file_info)
                    res_data = ("object_model", [("ota_status", (file_info[0], 1, file_info[2]))])
            elif errcode == 10701:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10702:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10703:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10704:
                res_data = ("object_model", [("ota_status", (None, 2, None))])
            elif errcode == 10705:
                res_data = ("object_model", [("ota_status", (None, 3, None))])
            elif errcode == 10706:
                res_data = ("object_model", [("ota_status", (None, 4, None))])

        if res_data:
            self.notifyObservers(self, *res_data)

        if event == 7 and errcode == 10701 and eventdata:
            file_info = eval(eventdata)
            self.__sota_download_info(int(file_info[1]), file_info[2])
        if event == 7 and errcode == 10703 and eventdata:
            file_info = eval(eventdata)
            log.info("OTA File Info: componentNo: %s, length: %s, md5: %s, crc: %s" % file_info)
            self.__sota_upgrade_start(int(file_info[2]), int(file_info[3]))

    def cloud_init(self, enforce=False):
        log.debug(
            "[cloud_init start] enforce: %s QuecThing Work State: %s, quecIot.getConnmode(): %s"
            % (enforce, quecIot.getWorkState(), quecIot.getConnmode())
        )
        if enforce is False:
            if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
                return True

        quecIot.init()
        quecIot.setEventCB(self.__event_cb)
        quecIot.setProductinfo(self.pk, self.ps)
        if self.dk or self.ds:
            quecIot.setDkDs(self.dk, self.ds)
        quecIot.setServer(1, self.server)
        quecIot.setLifetime(self.life_time)
        quecIot.setMcuVersion(self.mcu_name, self.mcu_version)
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
                    log.debug("dk: %s, ds: %s" % dkds)
                    res_data = (
                        "object_model",
                        [("cloud_init_params", {"PK": self.pk, "PS": self.ps, "DK": self.dk, "DS": self.ds, "SERVER": self.server})]
                    )
                    self.notifyObservers(self, *res_data)
                    break
                count += 1
                utime.sleep(count)

        log.debug("[cloud_init over] QuecThing Work State: %s, quecIot.getConnmode(): %s" % (quecIot.getWorkState(), quecIot.getConnmode()))
        if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
            return True
        else:
            return False

    def cloud_close(self):
        return quecIot.setConnmode(0)

    def get_loc_data(self, loc_method, loc_data):
        if loc_method == 0x1:
            res = {"gps": []}
            gps_parsing = GPSParsing()
            r = gps_parsing.read_GxRMC(loc_data)
            if r:
                res["gps"].append(r)

            r = gps_parsing.read_GxGGA(loc_data)
            if r:
                res["gps"].append(r)

            r = gps_parsing.read_GxVTG(loc_data)
            if r:
                res["gps"].append(r)
            return res
        elif loc_method == 0x2:
            return {"non_gps": ["LBS"]}
        elif loc_method == 0x4:
            return {"non_gps": []}

    def post_data(self, data):
        res = True
        # log.debug("post_data: %s" % str(data))
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
                    # log.debug("k: %s, v: %s" % (k, v))
                    phymodelReport_res = quecIot.phymodelReport(1, {object_model_code.get(k): v})
                    if not phymodelReport_res:
                        res = False
                        break
                else:
                    continue
            elif k == "gps":
                locReportOutside_res = quecIot.locReportOutside(v)
                if not locReportOutside_res:
                    res = False
                    break
            elif k == "non_gps":
                locReportInside_res = quecIot.locReportInside(v)
                if not locReportInside_res:
                    res = False
                    break
            else:
                v = {}
                continue

            res = self.__get_post_res()
            if res:
                v = {}
            else:
                res = False
                break

        self.__rm_empty_data(data)
        return res

    def ota_request(self, mp_mode=0):
        return quecIot.otaRequest(mp_mode) if mp_mode in (0, 1) else False

    def ota_action(self, action=1, module=None):
        return quecIot.otaAction(action) if action in (0, 1, 2, 3) else False
