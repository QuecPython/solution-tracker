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

import ujson
import utime
import _thread
import osTimer

from aLiYun import aLiYun

from usr.logging import getLogger
from usr.common import numiter, option_lock, CloudObservable, CloudObjectModel

log = getLogger(__name__)

_gps_read_lock = _thread.allocate_lock()


class AliObjectModel(CloudObjectModel):

    def __init__(self):
        super().__init__()


class AliYunIot(CloudObservable):

    def __init__(self, pk, ps, dk, ds, server, client_id, burning_method=0, life_time=120,
                 mcu_name="", mcu_version="", firmware_name="", firmware_version=""):
        super().__init__()
        self.__pk = pk
        self.__ps = ps
        self.__dk = dk
        self.__ds = ds
        self.__server = server
        self.__burning_method = burning_method
        self.__life_time = life_time
        self.__mcu_name = mcu_name
        self.__mcu_version = mcu_version
        self.__firmware_name = firmware_name
        self.__firmware_version = firmware_version
        self.__object_model = None
        self.__client_id = client_id

        self.__ali = None
        self.__post_res = {}
        self.__breack_flag = 0
        self.__ali_timer = osTimer()

        self.__id_iter = numiter()
        self.__id_lock = _thread.allocate_lock()

        self.ica_topic_property_post = "/sys/%s/%s/thing/event/property/post" % (self.__pk, self.__dk)
        self.ica_topic_property_post_reply = "/sys/%s/%s/thing/event/property/post_reply" % (self.__pk, self.__dk)
        self.ica_topic_property_set = "/sys/%s/%s/thing/service/property/set" % (self.__pk, self.__dk)
        self.ica_topic_property_get = "/sys/%s/%s/thing/service/property/get" % (self.__pk, self.__dk)
        self.ica_topic_property_query = "/sys/%s/%s/thing/service/property/query" % (self.__pk, self.__dk)
        self.ica_topic_event_post = "/sys/%s/%s/thing/event/{}/post" % (self.__pk, self.__dk)
        self.ica_topic_event_post_reply = "/sys/%s/%s/thing/event/{}/post_reply" % (self.__pk, self.__dk)
        self.ota_topic_device_inform = "/ota/device/inform/%s/%s" % (self.__pk, self.__dk)
        self.ota_topic_device_upgrade = "/ota/device/upgrade/%s/%s" % (self.__pk, self.__dk)
        self.ota_topic_device_progress = "/ota/device/progress/%s/%s" % (self.__pk, self.__dk)
        self.ota_topic_firmware_get = "/sys/%s/%s/thing/ota/firmware/get" % (self.__pk, self.__dk)
        self.ota_topic_firmware_get_reply = "/sys/%s/%s/thing/ota/firmware/get_reply" % (self.__pk, self.__dk)

        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        self.ota_topic_file_download = "/sys/%s/%s/thing/file/download" % (self.__pk, self.__dk)
        self.ota_topic_file_download_reply = "/sys/%s/%s/thing/file/download_reply" % (self.__pk, self.__dk)

        self.rrpc_topic_request = "/sys/%s/%s/rrpc/request/+" % (self.__pk, self.__dk)
        self.rrpc_topic_response = "/sys/%s/%s/rrpc/response/{}" % (self.__pk, self.__dk)

    def __get_id(self):
        with self.__id_lock:
            try:
                msg_id = next(self.__id_iter)
            except StopIteration:
                self.__id_iter = numiter()
                msg_id = next(self.__id_iter)

        return str(msg_id)

    def __put_post_res(self, msg_id, res):
        self.__post_res[msg_id] = res

    def __ali_timer_cb(self, args):
        self.__breack_flag = 1

    @option_lock(_gps_read_lock)
    def __get_post_res(self, msg_id):
        self.__ali_timer.start(1000 * 10, 0, self.__ali_timer_cb)
        while self.__post_res.get(msg_id) is None:
            if self.__breack_flag:
                self.__post_res[msg_id] = False
                break
            utime.sleep_ms(50)
        self.__ali_timer.stop()
        self.__breack_flag = 0
        res = self.__post_res.pop(msg_id)
        return res

    def __ali_subcribe_topic(self):
        if self.__ali.subscribe(self.ica_topic_property_post, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_post)
        if self.__ali.subscribe(self.ica_topic_property_post_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_post_reply)
        if self.__ali.subscribe(self.ica_topic_property_set, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_set)
        if self.__ali.subscribe(self.ica_topic_property_get, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_get)
        if self.__ali.subscribe(self.ica_topic_property_query, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_query)
        for tsl_event_identifier in self.__object_model.items["event"].keys():
            post_topic = self.ica_topic_event_post.format(tsl_event_identifier)
            if self.__ali.subscribe(post_topic, qos=0) == -1:
                log.error("Topic [%s] Subscribe Falied." % post_topic)

            post_reply_topic = self.ica_topic_event_post_reply.format(tsl_event_identifier)
            if self.__ali.subscribe(post_reply_topic, qos=0) == -1:
                log.error("Topic [%s] Subscribe Falied." % post_reply_topic)

        if self.__ali.subscribe(self.ota_topic_device_upgrade, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ota_topic_device_upgrade)
        if self.__ali.subscribe(self.ota_topic_firmware_get_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ota_topic_firmware_get_reply)

        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        if self.__ali.subscribe(self.ota_topic_file_download_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ota_topic_file_download_reply)

        if self.__ali.subscribe(self.rrpc_topic_request, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.rrpc_topic_request)

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
        elif topic.find("/rrpc/request/") != -1:
            self.notifyObservers(self, *("rrpc_request", topic, data))
        else:
            pass

    def __data_format(self, data):
        res = {"event": [], "property": [], "msg_ids": [], "event_topic": {}}
        property_params = {}
        event_params = {}
        # Format Publish Params.
        for k, v in data.items():
            if k in self.__object_model.items["property"].keys():
                property_params[k] = {
                    "value": v,
                    "time": utime.mktime(utime.localtime()) * 1000
                }
            elif k in self.__object_model.items["event"].keys():
                event_params[k] = {
                    "value": {},
                    "time": utime.mktime(utime.localtime()) * 1000
                }
            else:
                log.error("Publish Key [%s] is not in property and event" % k)

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
            res["property"].append(publish_data)
            res["msg_ids"].append(msg_id)

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
                res["event"].append(publish_data)
                res["event_topic"][msg_id] = topic
                res["msg_ids"].append(msg_id)

        return res

    def set_object_model(self, object_model):
        if object_model and isinstance(object_model, AliObjectModel):
            self.__object_model = object_model
            return True
        return False

    def init(self, enforce=False):
        log.debug("[init start] enforce: %s" % enforce)
        if enforce is False and self.__ali is not None:
            log.debug("self.__ali.getAliyunSta(): %s" % self.__ali.getAliyunSta())
            if self.__ali.getAliyunSta() == 0:
                return True

        if self.__burning_method == 0:
            self.__dk = None
        elif self.__burning_method == 1:
            self.__ps = None

        log.debug("aLiYun init. self.__pk: %s, self.__ps: %s, self.__dk: %s, self.__ds: %s, self.__server: %s" % (self.__pk, self.__ps, self.__dk, self.__ds, self.__server))
        self.__ali = aLiYun(self.__pk, self.__ps, self.__dk, self.__ds, self.__server)
        log.debug("aLiYun setMqtt.")
        setMqttres = self.__ali.setMqtt(self.__client_id, clean_session=False, keepAlive=self.__life_time, reconn=True)
        log.debug("aLiYun setMqttres: %s" % setMqttres)
        if setMqttres != -1:
            self.__ali.setCallback(self.__ali_sub_cb)
            self.__ali_subcribe_topic()
            self.__ali.start()
        else:
            log.error("setMqtt Falied!")
            return False

        log.debug("self.__ali.getAliyunSta(): %s" % self.__ali.getAliyunSta())
        if self.__ali.getAliyunSta() == 0:
            return True
        else:
            return False

    def close(self):
        self.__ali.disconnect()
        return True

    def post_data(self, data):
        if self.__ali.getAliyunSta() == 0:
            try:
                publish_data = self.__data_format(data)
                # Publish Property Data.
                for item in publish_data["property"]:
                    self.__ali.publish(self.ica_topic_property_post, ujson.dumps(item), qos=0)
                # Publish Event Data.
                for item in publish_data["event"]:
                    self.__ali.publish(publish_data["event_topic"][item["id"]], ujson.dumps(item), qos=0)
                pub_res = [self.__get_post_res(msg_id) for msg_id in publish_data["msg_ids"]]
                return True if False not in pub_res else False
            except Exception:
                log.error("AliYun publish topic %s failed. data: %s" % (data.get("topic"), data.get("data")))

        return False

    def rrpc_response(self, message_id, data):
        topic = self.rrpc_topic_response.format(message_id)
        pub_data = ujson.dumps(data) if isinstance(data, dict) else data
        self.__ali.publish(topic, pub_data, qos=0)
        return True

    def device_report(self):
        muc_res = self.ota_device_inform(self.__mcu_version, module=self.__mcu_name)
        fw_res = self.ota_device_inform(self.__firmware_version, module=self.__firmware_name)
        return True if muc_res and fw_res else False

    def ota_request(self):
        sota_res = self.ota_firmware_get(self.__mcu_name)
        fota_res = self.ota_firmware_get(self.__firmware_name)
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
        publish_res = self.__ali.publish(self.ota_topic_device_inform, ujson.dumps(publish_data), qos=0)
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
        publish_res = self.__ali.publish(self.ota_topic_device_progress, ujson.dumps(publish_data), qos=0)
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
        publish_res = self.__ali.publish(self.ota_topic_firmware_get, ujson.dumps(publish_data), qos=0)
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
        publish_res = self.__ali.publish(self.ota_topic_file_download, ujson.dumps(publish_data), qos=0)
        if publish_res:
            return self.__get_post_res(msg_id)
        else:
            log.error("ota_file_download publish_res: %s" % publish_res)
            return False
