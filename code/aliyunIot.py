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

import ure
import ujson
import utime
import modem
import _thread
import osTimer

from aLiYun import aLiYun

from usr.common import numiter
from usr.common import option_lock
from usr.common import CloudObservable
from usr.logging import getLogger
from usr.location import GPSParsing

log = getLogger(__name__)

object_model = {
    "event": [
        "sos_alert",
        "fault_alert",
        "low_power_alert",
        "sim_abnormal_alert",
        "disassemble_alert",
        "drive_behavior_alert",
        "over_speed_alert",
    ],
    "property": [
        "power_switch",
        "energy",
        "phone_num",
        "loc_method",
        "work_mode",
        "work_cycle_period",
        "local_time",
        "low_power_alert_threshold",
        "low_power_shutdown_threshold",
        "sw_ota",
        "sw_ota_auto_upgrade",
        "sw_voice_listen",
        "sw_voice_record",
        "sw_fault_alert",
        "sw_low_power_alert",
        "sw_over_speed_alert",
        "sw_sim_abnormal_alert",
        "sw_disassemble_alert",
        "sw_drive_behavior_alert",
        "drive_behavior_code",
        "power_restart",
        "over_speed_threshold",
        "device_module_status",
        "gps_mode",
        "user_ota_action",
        "ota_status",
        "GeoLocation",
        "voltage",
    ],
}

_gps_read_lock = _thread.allocate_lock()


class AliYunIot(CloudObservable):

    def __init__(self, pk, ps, dk, ds, server, burning_method=0, life_time=120,
                 mcu_name="", mcu_version="", firmware_name="", firmware_version=""):
        super().__init__()
        self.pk = pk
        self.ps = ps
        self.dk = dk
        self.ds = ds
        self.server = server
        self.burning_method = burning_method
        self.life_time = life_time
        self.mcu_name = mcu_name
        self.mcu_version = mcu_version
        self.firmware_name = firmware_name
        self.firmware_version = firmware_version

        self.ali = None
        self.post_res = {}
        self.breack_flag = 0
        self.ali_timer = osTimer()

        self.id_iter = numiter()
        self.id_lock = _thread.allocate_lock()

        self.ica_topic_property_post = "/sys/%s/%s/thing/event/property/post" % (self.pk, self.dk)
        self.ica_topic_property_post_reply = "/sys/%s/%s/thing/event/property/post_reply" % (self.pk, self.dk)
        self.ica_topic_property_set = "/sys/%s/%s/thing/service/property/set" % (self.pk, self.dk)
        self.ica_topic_property_get = "/sys/%s/%s/thing/service/property/get" % (self.pk, self.dk)
        self.ica_topic_property_query = "/sys/%s/%s/thing/service/property/query" % (self.pk, self.dk)
        self.ica_topic_event_post = "/sys/%s/%s/thing/event/{}/post" % (self.pk, self.dk)
        self.ica_topic_event_post_reply = "/sys/%s/%s/thing/event/{}/post_reply" % (self.pk, self.dk)
        self.ota_topic_device_inform = "/ota/device/inform/%s/%s" % (self.pk, self.dk)
        self.ota_topic_device_upgrade = "/ota/device/upgrade/%s/%s" % (self.pk, self.dk)
        self.ota_topic_device_progress = "/ota/device/progress/%s/%s" % (self.pk, self.dk)
        self.ota_topic_firmware_get = "/sys/%s/%s/thing/ota/firmware/get" % (self.pk, self.dk)
        self.ota_topic_firmware_get_reply = "/sys/%s/%s/thing/ota/firmware/get_reply" % (self.pk, self.dk)

        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        self.ota_topic_file_download = "/sys/%s/%s/thing/file/download" % (self.pk, self.dk)
        self.ota_topic_file_download_reply = "/sys/%s/%s/thing/file/download_reply" % (self.pk, self.dk)

    def __get_id(self):
        with self.id_lock:
            try:
                msg_id = next(self.id_iter)
            except StopIteration:
                self.id_iter = numiter()
                msg_id = next(self.id_iter)

        return str(msg_id)

    def __put_post_res(self, msg_id, res):
        self.post_res[msg_id] = res

    def __ali_timer_cb(self, args):
        self.breack_flag = 1

    @option_lock(_gps_read_lock)
    def __get_post_res(self, msg_id):
        self.ali_timer.start(5 * 1000, 0, self.__ali_timer_cb)
        while self.post_res.get(msg_id) is None:
            if self.breack_flag:
                self.post_res[msg_id] = False
                break
            utime.sleep_ms(50)
        self.ali_timer.stop()
        self.breack_flag = 0
        res = self.post_res.pop(msg_id)
        return res

    def __ali_subcribe_topic(self):
        if self.ali.subscribe(self.ica_topic_property_post, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_post)
        if self.ali.subscribe(self.ica_topic_property_post_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_post_reply)
        if self.ali.subscribe(self.ica_topic_property_set, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_set)
        if self.ali.subscribe(self.ica_topic_property_get, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_get)
        if self.ali.subscribe(self.ica_topic_property_query, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_query)
        for tsl_event_identifier in object_model["event"]:
            post_topic = self.ica_topic_event_post.format(tsl_event_identifier)
            if self.ali.subscribe(post_topic, qos=0) == -1:
                log.error("Topic [%s] Subscribe Falied." % post_topic)

            post_reply_topic = self.ica_topic_event_post_reply.format(tsl_event_identifier)
            if self.ali.subscribe(post_reply_topic, qos=0) == -1:
                log.error("Topic [%s] Subscribe Falied." % post_reply_topic)

        if self.ali.subscribe(self.ota_topic_device_upgrade, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ota_topic_device_upgrade)
        if self.ali.subscribe(self.ota_topic_firmware_get_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ota_topic_firmware_get_reply)

        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        if self.ali.subscribe(self.ota_topic_file_download_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ota_topic_file_download_reply)

    def __ali_sub_cb(self, topic, data):
        topic = topic.decode()
        data = ujson.loads(data)
        log.info("topic: %s, data: %s" % (topic, data))
        if topic.endswith("/post_reply"):
            self.__put_post_res(data["id"], True if data["code"] == 200 else False)
        elif topic.endswith("/property/set"):
            if data["method"] == "thing.service.property.set":
                dl_data = list(zip(data.get("params", {}).keys(), data.get("params", {}).values()))
                self.notifyObservers(self, *("object_model", dl_data))
        elif topic.startswith("/ota/device/upgrade/"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 1000 else False)
            if int(data["code"]) == 1000:
                if data.get("data"):
                    self.notifyObservers(self, *("object_model", [("ota_status", (data["data"]["module"], 1, data["data"]["version"]))]))
                    self.notifyObservers(self, *("ota_plain", data["data"]))
        elif topic.endswith("/thing/ota/firmware/get_reply"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 200 else False)
            if data["code"] == 200:
                if data.get("data"):
                    self.notifyObservers(self, *("object_model", [("ota_status", (data["data"]["module"], 1, data["data"]["version"]))]))
                    self.notifyObservers(self, *("ota_plain", data["data"]))
        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        elif topic.endswith("/thing/file/download_reply"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 200 else False)
            if data["code"] == 200:
                self.notifyObservers(self, *("ota_file_download", data["data"]))
        else:
            pass

    def get_loc_data(self, loc_method, loc_data):
        res = {"GeoLocation": {}}

        if loc_method == 0x1:
            gps_parsing = GPSParsing()
            gga_data = gps_parsing.read_GxGGA(loc_data)
            data = {}
            if gga_data:
                Latitude_re = ure.search(r",[0-9]+\.[0-9]+,[NS],", gga_data)
                if Latitude_re:
                    data["Latitude"] = round(float(Latitude_re.group(0)[1:-3]), 2)
                Longtitude_re = ure.search(r",[0-9]+\.[0-9]+,[EW],", gga_data)
                if Longtitude_re:
                    data["Longtitude"] = round(float(Longtitude_re.group(0)[1:-3]), 2)
                Altitude_re = ure.search(r"-*[0-9]+\.[0-9]+,M,", gga_data)
                if Altitude_re:
                    data["Altitude"] = round(float(Altitude_re.group(0)[:-3]), 2)
                if data:
                    data["CoordinateSystem"] = 1
            res = {"GeoLocation": data}
        elif loc_method in (0x2, 0x4):
            if loc_data:
                res["GeoLocation"] = {
                    "Longtitude": round(loc_data[0], 2),
                    "Latitude": round(loc_data[1], 2),
                    # "Altitude": 0.0,
                    "CoordinateSystem": 1
                }

        return res

    def cloud_init(self, enforce=False):
        log.debug("[cloud_init start] enforce: %s" % enforce)
        if enforce is False and self.ali is not None:
            log.debug("self.ali.getAliyunSta(): %s" % self.ali.getAliyunSta())
            if self.ali.getAliyunSta() == 0:
                return True

        if self.burning_method == 0:
            self.dk = None
        elif self.burning_method == 1:
            self.ps = None

        log.debug("aLiYun init. self.pk: %s, self.ps: %s, self.dk: %s, self.ds: %s, self.server: %s" % (self.pk, self.ps, self.dk, self.ds, self.server))
        self.ali = aLiYun(self.pk, self.ps, self.dk, self.ds, self.server)
        log.debug("aLiYun setMqtt.")
        clientId = modem.getDevImei()
        log.debug("aLiYun clientId(IMEI): %s" % clientId)
        setMqttres = self.ali.setMqtt(clientId, clean_session=False, keepAlive=self.life_time, reconn=True)
        log.debug("aLiYun setMqttres: %s" % setMqttres)
        if setMqttres != -1:
            self.ali.setCallback(self.__ali_sub_cb)
            self.__ali_subcribe_topic()
            self.ali.start()
        else:
            log.error("setMqtt Falied!")
            return False

        log.debug("self.ali.getAliyunSta(): %s" % self.ali.getAliyunSta())
        if self.ali.getAliyunSta() == 0:
            return True
        else:
            return False

    def cloud_close(self):
        self.ali.disconnect()

    def post_data(self, data):
        msg_ids = []
        if self.ali.getAliyunSta() == 0:
            try:
                property_params = {}
                event_params = {}
                # Format Publish Params.
                for k, v in data.items():
                    if k in object_model["property"]:
                        property_params[k] = {
                            "value": v,
                            "time": utime.mktime(utime.localtime()) * 1000
                        }
                    elif k in object_model["event"]:
                        event_params[k] = {
                            "value": {},
                            "time": utime.mktime(utime.localtime()) * 1000
                        }
                    else:
                        log.error("Publish Key [%s] is not in property and event" % k)
                # Publish Property Data.
                if property_params:
                    msg_id = self.__get_id()
                    publish_data = {
                        "id": msg_id,
                        "version": "1.0",
                        "sys": {
                            "ack": 1
                        },
                        "params": property_params,
                        "method": "thing.event.property.post"
                    }
                    self.ali.publish(self.ica_topic_property_post, ujson.dumps(publish_data), qos=0)
                    msg_ids.append(msg_id)
                # Publish Event Data.
                if event_params:
                    for event in event_params.keys():
                        topic = self.ica_topic_event_post.format(event)
                        msg_id = self.__get_id()
                        publish_data = {
                            "id": msg_id,
                            "version": "1.0",
                            "sys": {
                                "ack": 1
                            },
                            "params": event_params[event],
                            "method": "thing.event.%s.post" % event
                        }
                        self.ali.publish(topic, ujson.dumps(publish_data), qos=0)
                        msg_ids.append(msg_id)

                pub_res = [self.__get_post_res(msg_id) for msg_id in msg_ids]
                return True if False not in pub_res else False
            except Exception:
                log.error("AliYun publish topic %s failed. data: %s" % (data.get("topic"), data.get("data")))

        return False

    def device_report(self):
        muc_res = self.ota_device_inform(self.mcu_version, module=self.mcu_name)
        fw_res = self.ota_device_inform(self.firmware_version, module=self.firmware_name)
        return True if muc_res and fw_res else False

    def ota_request(self):
        sota_res = self.ota_firmware_get(self.mcu_name)
        fota_res = self.ota_firmware_get(self.firmware_name)
        return True if sota_res and fota_res else False

    def ota_action(self, action, module=None):
        if not module:
            log.error("Params[module] Is Empty.")
            return False
        if action not in (0, 1):
            log.error("Params[action] Should Be 0 Or 1, Not %s." % action)
            return False

        if action == 1:
            return self.ota_device_progress(step=1, module=module)
        else:
            return self.ota_device_progress(step=-1, desc="User cancels upgrade.", module=module)

    def ota_device_inform(self, version, module="default"):
        msg_id = self.__get_id()
        publish_data = {
            "id": msg_id,
            "params": {
                "version": version,
                "module": module,
            },
        }
        publish_res = self.ali.publish(self.ota_topic_device_inform, ujson.dumps(publish_data), qos=0)
        log.debug("version: %s, module: %s, publish_res: %s" % (version, module, publish_res))
        return publish_res

    def ota_device_progress(self, step, desc, module="default"):
        msg_id = self.__get_id()
        publish_data = {
            "id": msg_id,
            "params": {
                "step": step,
                "desc": desc,
                "module": module,
            }
        }
        publish_res = self.ali.publish(self.ota_topic_device_progress, ujson.dumps(publish_data), qos=0)
        if publish_res:
            return self.__get_post_res(msg_id)
        else:
            log.error("ota_device_progress publish_res: %s" % publish_res)
            return False

    def ota_firmware_get(self, module):
        msg_id = self.__get_id()
        publish_data = {
            "id": msg_id,
            "version": "1.0",
            "params": {
                "module": module,
            },
            "method": "thing.ota.firmware.get"
        }
        publish_res = self.ali.publish(self.ota_topic_firmware_get, ujson.dumps(publish_data), qos=0)
        log.debug("module: %s, publish_res: %s" % (module, publish_res))
        if publish_res:
            return self.__get_post_res(msg_id)
        else:
            log.error("ota_firmware_get publish_res: %s" % publish_res)
            return False

    def ota_file_download(self, params):
        msg_id = self.__get_id()
        publish_data = {
            "id": msg_id,
            "version": "1.0",
            "params": params
        }
        publish_res = self.ali.publish(self.ota_topic_file_download, ujson.dumps(publish_data), qos=0)
        if publish_res:
            return self.__get_post_res(msg_id)
        else:
            log.error("ota_file_download publish_res: %s" % publish_res)
            return False
