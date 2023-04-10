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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@file      :thingsboard_mqtt.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :<description>
@version   :1.0.0
@date      :2022-09-14 11:04:03
@copyright :Copyright (c) 2022
"""

import usys
import utime
import ujson
import _thread
from umqtt import MQTTClient
from usr.logging import getLogger

log = getLogger(__name__)

TELEMETRY_TOPIC = 'v1/devices/me/telemetry'
RPC_RESPONSE_TOPIC = 'v1/devices/me/rpc/response/'
RPC_REQUEST_TOPIC = 'v1/devices/me/rpc/request/'

# cloud_mqtt_cfg = {
#     "host": "106.15.58.32",
#     "port": 1883,
#     "username": "ryy8Q0nreru1OinVGxwo",
#     "quality_of_service": 0,
#     "client_id": "03c7d510-538f-11ed-b00f-a9b90aa15227",
#     "chunk_size": 0,
# }


class TBDeviceMQTTClient:

    def __init__(self, host, port=1883, username=None, password="", quality_of_service=0, client_id="", chunk_size=0):
        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__quality_of_service = quality_of_service
        self.__client_id = client_id
        self.__chunk_size = chunk_size
        self.__mqtt = None
        self.__callback = print
        self.__status = False
        self.__thread_id = None

    def __wait_msg(self):
        """This function is in a thread to wait server downlink message."""
        while True:
            try:
                if self.__mqtt:
                    self.__mqtt.wait_msg()
            except Exception as e:
                usys.print_exception(e)
                log.error(e)
            finally:
                utime.sleep_ms(100)

    def __start_wait_msg(self):
        """Start a thread to wait server message and save this thread id."""
        _thread.stack_size(0x2000)
        self.__thread_id = _thread.start_new_thread(self.__wait_msg, ())

    def __stop_wait_msg(self):
        """Stop the thread for waiting server message."""
        if self.__thread_id is not None:
            _thread.stop_thread(self.__thread_id)
            self.__thread_id = None

    @property
    def status(self):
        return self.__status
        state = self.__mqtt.get_mqttsta() if self.__mqtt else -1
        log.debug("mqtt state: %s" % state)
        return True if state == 0 else False

    def set_callback(self, callback):
        if callable(callback):
            self.__callback = callback
            return True
        return False

    def connect(self, clean_session=True):
        try:
            self.__mqtt = MQTTClient(self.__client_id, self.__host, self.__port, self.__username, self.__password, keepalive=60, reconn=True)
            self.__mqtt.set_callback(self.__callback)
            if self.__mqtt.connect(clean_session=clean_session) == 0:
                self.__status = True
                self.__mqtt.subscribe(RPC_REQUEST_TOPIC + "+", self.__quality_of_service)
                self.__start_wait_msg()
                return True
        except Exception as e:
            usys.print_exception(e)
        return False

    def disconnect(self):
        try:
            if self.__mqtt:
                self.__mqtt.disconnect()
                self.__mqtt = None
                self.__stop_wait_msg()
            return True
        except Exception as e:
            usys.print_exception(e)
        finally:
            self.__status = False
        return False

    def send_telemetry(self, data):
        try:
            self.__mqtt.publish(TELEMETRY_TOPIC, ujson.dumps(data), qos=self.__quality_of_service)
            return True
        except Exception as e:
            usys.print_exception(e)
        return False

    def send_rpc_reply(self, data, request_id):
        try:
            self.__mqtt.publish(RPC_RESPONSE_TOPIC + request_id, ujson.dumps(data), qos=self.__quality_of_service)
            return True
        except Exception as e:
            usys.print_exception(e)
        return False
