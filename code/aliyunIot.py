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
    """This class is aliyun object model

    This class extend CloudObjectModel.

    Attribute:
        items:
            - object model dictionary
            - data format:
            {
                "event": {
                    "name": "event",
                    "id": "",
                    "perm": "",
                    "struct_info": {
                        "name": "struct",
                        "id": "",
                        "struct_info": {
                            "key": {
                                "name": "key"
                            }
                        },
                    },
                },
                "property": {
                    "name": "event",
                    "id": "",
                    "perm": "",
                    "struct_info": {}
                }
            }
    """

    def __init__(self):
        super().__init__()


class AliYunIot(CloudObservable):
    """This is a class for aliyun iot.

    This class extend CloudObservable.

    This class has the following functions:
        1. Cloud connect and disconnect

        2. Publish data to cloud
        2.1 Publish object module
        2.2 Publish ota device info, ota upgrade process, ota plain info request
        2.3 Publish rrpc response

        3. Subscribe data from cloud
        3.1 Subscribe publish object model result
        3.2 Subscribe cloud message
        3.3 Subscribe ota plain
        3.4 Subscribe rrpc request

    Attribute:
        ica_topic_property_post: topic for publish object model property
        ica_topic_property_post_reply: topic for subscribe publish object model property result
        ica_topic_property_set: topic for subscribe cloud object model property set
        ica_topic_event_post: topic for publish object model event
        ica_topic_event_post_reply: topic for subscribe publish object model event result
        ota_topic_device_inform: topic for publish device information
        ota_topic_device_upgrade: topic for subscribe ota plain
        ota_topic_device_progress: topic for publish ota upgrade process
        ota_topic_firmware_get: topic for publish ota plain request
        ota_topic_firmware_get_reply: topic for subscribe ota plain request response
        ota_topic_file_download: topic for publish ota mqtt file download request
        ota_topic_file_download_reply: topic for publish ota mqtt file download request response
        rrpc_topic_request: topic for subscribe rrpc message
        rrpc_topic_response: topic for publish rrpc response

    Run step:
        1. cloud = AliYunIot(pk, ps, dk, ds, server, client_id)
        2. cloud.addObserver(RemoteSubscribe)
        3. cloud.set_object_model(AliObjectModel)
        4. cloud.init()
        5. cloud.post_data(data)
        6. cloud.close()
    """

    def __init__(self, pk, ps, dk, ds, server, client_id, burning_method=0, life_time=120,
                 mcu_name="", mcu_version="", firmware_name="", firmware_version=""):
        """
        1. Init parent class CloudObservable
        2. Init cloud connect params and topic
        """
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
        """Get message id for publishing data"""
        with self.__id_lock:
            try:
                msg_id = next(self.__id_iter)
            except StopIteration:
                self.__id_iter = numiter()
                msg_id = next(self.__id_iter)

        return str(msg_id)

    def __put_post_res(self, msg_id, res):
        """Save publish result by message id

        Parameter:
            msg_id: publish message id
            res: publish result, True or False
        """
        self.__post_res[msg_id] = res

    def __ali_timer_cb(self, args):
        """osTimer callback to break cycling of get publish result"""
        self.__breack_flag = 1

    @option_lock(_gps_read_lock)
    def __get_post_res(self, msg_id):
        """Get publish result by message id

        Parameter:
            msg_id: publish message id

        Return:
            True: publish success
            False: publish failed
        """
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

    def __ali_subscribe_topic(self):
        """Subscribe aliyun topic"""
        if self.__ali.subscribe(self.ica_topic_property_post, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_post)
        if self.__ali.subscribe(self.ica_topic_property_post_reply, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_post_reply)
        if self.__ali.subscribe(self.ica_topic_property_set, qos=0) == -1:
            log.error("Topic [%s] Subscribe Falied." % self.ica_topic_property_set)
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
        """Aliyun subscribe topic callback

        Parameter:
            topic: topic info
            data: response dictionary info
        """
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
        """Publish data format by AliObjectModel

        Parameter:
            data format:
            {
                "phone_num": "123456789",
                "energy": 100,
                "GeoLocation": {
                    "Longtitude": 100.26,
                    "Latitude": 26.86,
                    "Altitude": 0.0,
                    "CoordinateSystem": 1
                },
            }

        Return:
            {
                "event": [
                    {
                        "id": 1,
                        "version": "1.0",
                        "sys": {
                            "ack": 1
                        },
                        "params": {
                            "sos_alert": {
                                "value": {},
                                "time": 1649991780000
                            },
                        },
                        "method": "thing.event.sos_alert.post"
                    }
                ],
                "property": [
                    {
                        "id": 2,
                        "version": "1.0",
                        "sys": {
                            "ack": 1
                        },
                        "params": {
                            "phone_num": {
                                "value": "123456789",
                                "time": 1649991780000
                            },
                            "energy": {
                                "value": 100,
                                "time": 1649991780000
                            },
                        },
                        "method": "thing.event.property.post"
                    }
                ],
                "msg_ids": [1, 2],
                "event_topic": {
                    1: "/sys/{product_key}/{device_key}/thing/event/{event}/post",
                    2: "/sys/{product_key}/{device_key}/thing/event/property/post",
                }
            }
        """
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
        """Register AliObjectModel to this class"""
        if object_model and isinstance(object_model, AliObjectModel):
            self.__object_model = object_model
            return True
        return False

    def init(self, enforce=False):
        """Aliyun connect and subscribe topic

        Parameter:
            enforce:
                True: enfore cloud connect and subscribe topic
                False: check connect status, return True if cloud connected

        Return:
            Ture: Success
            False: Failed
        """
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
            self.__ali_subscribe_topic()
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
        """Aliyun disconnect"""
        self.__ali.disconnect()
        return True

    def post_data(self, data):
        """Publish object model property, event

        Parameter:
            data format:
            {
                "phone_num": "123456789",
                "energy": 100,
                "GeoLocation": {
                    "Longtitude": 100.26,
                    "Latitude": 26.86,
                    "Altitude": 0.0,
                    "CoordinateSystem": 1
                },
            }

        Return:
            Ture: Success
            False: Failed
        """
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
        """Publish rrpc response

        Parameter:
            message_id: rrpc request messasge id
            data: response message

        Return:
            Ture: Success
            False: Failed
        """
        topic = self.rrpc_topic_response.format(message_id)
        pub_data = ujson.dumps(data) if isinstance(data, dict) else data
        self.__ali.publish(topic, pub_data, qos=0)
        return True

    def device_report(self):
        """Publish mcu and firmware name, version

        Return:
            Ture: Success
            False: Failed
        """
        muc_res = self.ota_device_inform(self.__mcu_version, module=self.__mcu_name)
        fw_res = self.ota_device_inform(self.__firmware_version, module=self.__firmware_name)
        return True if muc_res and fw_res else False

    def ota_request(self):
        """Publish mcu and firmware ota plain request

        Return:
            Ture: Success
            False: Failed
        """
        sota_res = self.ota_firmware_get(self.__mcu_name)
        fota_res = self.ota_firmware_get(self.__firmware_name)
        return True if sota_res and fota_res else False

    def ota_action(self, action, module=None):
        """Publish ota upgrade start or cancel ota upgrade

        Parameter:
            action: confirm or cancel upgrade
                - 0: cancel upgrade
                - 1: confirm upgrade

            module: mcu or firmare model name
                - e.g.: `QuecPython-Tracker`, `EC600N-CNLC`

        Return:
            Ture: Success
            False: Failed
        """
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
        """Publish device information

        Parameter:
            version: module version
                - e.g.: `2.1.0`

            module: mcu or firmare model name
                - e.g.: `QuecPython-Tracker`

        Return:
            Ture: Success
            False: Failed
        """
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
        """Publish ota upgrade process

        Parameter:
            step: upgrade process
                - 1 ~ 100: Upgrade progress percentage
                - -1: Upgrade failed
                - -2: Download failed
                - -3: Verification failed
                - -4: Programming failed

            desc: Description of the current step, no more than 128 characters long. If an exception occurs, this field can carry error information.

            module: mcu or firmare model name
                - e.g.: `QuecPython-Tracker`

        Return:
            Ture: Success
            False: Failed
        """
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
        """Publish ota plain info request

        Parameter:
            module: mcu or firmare model name
                - e.g.: `QuecPython-Tracker`

        Return:
            Ture: Success
            False: Failed
        """
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
        """Publish mqtt ota plain file info request

        Parameter:
            params: file download info
            params format:
            {
                "fileToken": "1bb8***",
                "fileInfo": {
                    "streamId": 1234565,
                    "fileId": 1
                },
                "fileBlock": {
                    "size": 256,
                    "offset": 2
                }
            }

        Return:
            Ture: Success
            False: Failed
        """
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
