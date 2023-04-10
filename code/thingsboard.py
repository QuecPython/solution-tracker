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
@file      :thingsboard.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :<description>
@version   :1.0.0
@date      :2023-01-09 09:53:52
@copyright :Copyright (c) 2022
"""
import usys
import utime
import ujson
import modem
import _thread
from usr.common import SocketBase, SerialNo
from usr.logging import getLogger

log = getLogger(__name__)


class TBDeviceTCPClient(SocketBase):

    def __init__(self, host="220.180.239.212", port=9654, timeout=30, imei=modem.getDevImei()):
        super().__init__(host, port, method="TCP")
        self.__timeout = timeout
        self.__response_res = {}
        self.__read_thread = None
        self.__disconn_tag = 0
        self.__serial_no = SerialNo(start_no=1)
        self.__imei = imei

    def __read_response(self):
        message = b""
        while True:
            try:
                if super().status() not in (0, 1):
                    log.error("%s connection status is %s" % (self.__method, super().status()))
                    break

                # When read data is empty, discard message's data
                new_msg = self.__read()
                if new_msg:
                    message += new_msg
                else:
                    message = new_msg

                if message:
                    try:
                        data = ujson.loads(message)
                        if data.get("id") is not None:
                            self.__response_res[data.get("id")] = data
                        message = b""
                    except Exception as e:
                        usys.print_exception(e)
                        log.error("message: %s" % message)
            except Exception as e:
                usys.print_exception(e)
            finally:
                if self.__disconn_tag == 1:
                    super().disconnect()
                    break

    def __get_response(self, msg_no):
        res = {}
        count = 0
        while count < self.__timeout * 10:
            if self.__response_res.get(msg_no) is not None:
                res = self.__response_res.pop(msg_no)
                break
            utime.sleep_ms(100)
        return res if res else {"success": -1, "id": msg_no, "type": 0x00, "err_msg": "Wait response timeout.", "err_code": -1}

    def _downlink_thread_start(self):
        _thread.stack_size(0x2000)
        self.__read_thread = _thread.start_new_thread(self.__read_response, ())

    def _downlink_thread_stop(self):
        if self.__read_thread is not None:
            _thread.stop_thread(self.__read_thread)
            self.__read_thread = None

    def send(self, msg_type, data):
        msg_no = self.__serial_no.get_serial_no()
        _data = {"id": msg_no, "type": msg_type, "data": data}
        if data.get("imei") is None:
            _data.update({"imei": self.__imei})
        if self.__send(ujson.dumps(_data).encode()):
            return self.__get_response(msg_no)
        return {"success": -1, "id": msg_no, "type": 0x00, "err_msg": "Send data failed.", "err_code": -1}

    def register(self):
        return self.send(0x00, {"imei": self.__imei})

    def connect(self):
        self.__disconn_tag = 0
        if super().connect():
            reg_res = self.register()
            log.debug("register %s" % str(reg_res))
            if reg_res["success"] == 1:
                return True
        return False

    def disconnect(self):
        self.__disconn_tag = 1

    def send_telemetry(self, data):
        return self.send(0x01, data)

    @property
    def status(self):
        return True if super().status() == 0 else False
