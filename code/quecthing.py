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
from usr.logging import getLogger
from usr.common import CloudObservable, CloudObjectModel

log = getLogger(__name__)


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


class QuecObjectModel(CloudObjectModel):

    def __init__(self):
        super().__init__()
        self.items_id = {}

    def __init_items_id(self, om_key, om_key_id):
        self.items_id[om_key_id] = om_key
        return True

    def __del_items_id(self, om_type, om_key):
        if self.items.get(om_type) is not None:
            if self.items[om_type].get(om_key):
                om_key_id = self.items[om_type][om_key]["id"]
                self.items_id.pop(om_key_id)
        return True

    def set_item(self, om_type, om_key, om_key_id, om_key_perm):
        if super().set_item(om_type, om_key, om_key_id=om_key_id, om_key_perm=om_key_perm):
            self.__init_items_id(om_key, om_key_id)
            return True
        return False

    def del_item(self, om_type, om_key):
        self.__del_items_id(om_type, om_key)
        return super().del_item(om_type, om_key)


class QuecThing(CloudObservable):
    def __init__(self, pk, ps, dk, ds, server, life_time=120, mcu_name="", mcu_version=""):
        super().__init__()
        self.__pk = pk
        self.__ps = ps
        self.__dk = dk
        self.__ds = ds
        self.__server = server
        self.__life_time = life_time
        self.__mcu_name = mcu_name
        self.__mcu_version = mcu_version
        self.__object_model = None

        self.__file_size = 0
        self.__md5_value = ""
        self.__post_result_wait_queue = Queue(maxsize=16)
        self.__quec_timer = osTimer()

    def __rm_empty_data(self, data):
        for k, v in data.items():
            if not v:
                del data[k]

    def __quec_timer_cb(self, args):
        self.__put_post_res(False)

    def __get_post_res(self):
        self.__quec_timer.start(1000 * 10, 0, self.__quec_timer_cb)
        res = self.__post_result_wait_queue.get()
        self.__quec_timer.stop()
        return res

    def __put_post_res(self, res):
        if self.__post_result_wait_queue.size() >= 16:
            self.__post_result_wait_queue.get()
        self.__post_result_wait_queue.put(res)

    def __sota_download_info(self, size, md5_value):
        self.__file_size = size
        self.__md5_value = md5_value

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
            if (download_size == self.__file_size):
                log.debug("File Download Success, Update Start.")
                self.ota_action(3)
                if sota_mode.check_md5(self.__md5_value):
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

    def __data_format(self, k, v):
        # log.debug("k: %s, v: %s" % (k, v))
        k_id = None
        struct_info = {}
        if self.__object_model.items["event"].get(k):
            k_id = self.__object_model.items["event"][k]["id"]
            if isinstance(self.__object_model.items["event"][k]["struct_info"], dict):
                struct_info = self.__object_model.items["event"][k]["struct_info"]
        elif self.__object_model.items["property"].get(k):
            k_id = self.__object_model.items["property"][k]["id"]
            if isinstance(self.__object_model.items["property"][k]["struct_info"], dict):
                struct_info = self.__object_model.items["property"][k]["struct_info"]
        else:
            return False

        if isinstance(v, dict):
            nv = {}
            for ik, iv in v.items():
                if struct_info.get(ik):
                    nv[struct_info[ik]["id"]] = iv
                else:
                    nv[ik] = iv
            v = nv

        return {k_id: v}

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
                dl_data = [(self.__object_model.items_id[k], v.decode() if isinstance(v, bytes) else v) for k, v in eventdata.items()]
                res_data = ("object_model", dl_data)
            elif errcode == 10211:
                # eventdata[0] is pkgId.
                object_model_ids = eventdata[1]
                object_model_val = [self.__object_model.items_id[i] for i in object_model_ids if self.__object_model.items_id.get(i)]
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

    def set_object_model(self, object_model):
        if object_model and isinstance(object_model, QuecObjectModel):
            self.__object_model = object_model
            return True
        return False

    def init(self, enforce=False):
        log.debug(
            "[init start] enforce: %s QuecThing Work State: %s, quecIot.getConnmode(): %s"
            % (enforce, quecIot.getWorkState(), quecIot.getConnmode())
        )
        log.debug("[init start] PK: %s, PS: %s, DK: %s, DS: %s, SERVER: %s" % (self.__pk, self.__ps, self.__dk, self.__ds, self.__server))
        if enforce is False:
            if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
                return True

        quecIot.init()
        quecIot.setEventCB(self.__event_cb)
        quecIot.setProductinfo(self.__pk, self.__ps)
        if self.__dk or self.__ds:
            quecIot.setDkDs(self.__dk, self.__ds)
        quecIot.setServer(1, self.__server)
        quecIot.setLifetime(self.__life_time)
        quecIot.setMcuVersion(self.__mcu_name, self.__mcu_version)
        quecIot.setConnmode(1)

        count = 0
        while quecIot.getWorkState() != 8 and count < 10:
            utime.sleep_ms(200)
            count += 1

        if not self.__ds and self.__dk:
            count = 0
            while count < 3:
                dkds = quecIot.getDkDs()
                if dkds:
                    self.__dk, self.__ds = dkds
                    log.debug("dk: %s, ds: %s" % dkds)
                    res_data = (
                        "object_model",
                        [("init_params", {"PK": self.__pk, "PS": self.__ps, "DK": self.__dk, "DS": self.__ds, "SERVER": self.__server})]
                    )
                    self.notifyObservers(self, *res_data)
                    break
                count += 1
                utime.sleep(count)

        log.debug("[init over] QuecThing Work State: %s, quecIot.getConnmode(): %s" % (quecIot.getWorkState(), quecIot.getConnmode()))
        if quecIot.getWorkState() == 8 and quecIot.getConnmode() == 1:
            return True
        else:
            return False

    def close(self):
        return quecIot.setConnmode(0)

    def post_data(self, data):
        res = True
        # log.debug("post_data: %s" % str(data))
        for k, v in data.items():
            om_data = self.__data_format(k, v)
            if om_data is not False:
                if v is not None:
                    phymodelReport_res = quecIot.phymodelReport(1, om_data)
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
