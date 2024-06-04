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
import usys
import _thread
import usocket
from usr.logging import getLogger

log = getLogger(__name__)

_socket_lock = _thread.allocate_lock()
_serial_no_lock = _thread.allocate_lock()


def option_lock(thread_lock):
    """Function thread lock decorator"""
    def function_lock(func):
        def wrapperd_fun(*args, **kwargs):
            with thread_lock:
                return func(*args, **kwargs)
        return wrapperd_fun
    return function_lock


class Singleton(object):
    """Singleton base class"""
    _instance_lock = _thread.allocate_lock()

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance_dict"):
            Singleton.instance_dict = {}

        if str(cls) not in Singleton.instance_dict.keys():
            with Singleton._instance_lock:
                _instance = super().__new__(cls)
                Singleton.instance_dict[str(cls)] = _instance

        return Singleton.instance_dict[str(cls)]


class SerialNo(Singleton):

    def __init__(self, start_no=0):
        self.__start_no = start_no
        self.__num = 0xFFFF
        self.__init_iter_serial_no()

    def __init_iter_serial_no(self):
        self.__iter_serial_no = iter(range(self.__start_no, self.__num))

    @option_lock(_serial_no_lock)
    def get_serial_no(self):
        """Get message serial number.

        Returns:
            int: serial number
        """
        try:
            return next(self.__iter_serial_no)
        except StopIteration:
            self.__init_iter_serial_no()
            return self.get_serial_no()


class SocketBase:
    """This class is socket base"""

    def __init__(self, ip=None, port=None, domain=None, method="TCP"):
        """
        Args:
            ip: server ip address (default: {None})
            port: server port (default: {None})
            domain: server domain (default: {None})
            method: TCP or UDP (default: {"TCP"})
        """
        self.__ip = ip
        self.__port = port
        self.__domain = domain
        self.__addr = None
        self.__method = method
        self.__socket = None
        self.__socket_args = []
        self.__timeout = 5
        self.__init_addr()
        self.__init_socket()

    def __init_addr(self):
        """Get ip and port from domain.

        Raises:
            ValueError: Domain DNS parsing falied.
        """
        if self.__domain is not None and self.__domain:
            if self.__port is None:
                self.__port == 8883 if self.__domain.startswith("https://") else 1883
            try:
                addr_info = usocket.getaddrinfo(self.__domain, self.__port)
                self.__ip = addr_info[0][-1][0]
            except Exception as e:
                usys.print_exception(e)
                raise ValueError("Domain %s DNS parsing error. %s" % (self.__domain, str(e)))
        self.__addr = (self.__ip, self.__port)

    def __init_socket(self):
        """Init socket by ip, port and method

        Raises:
            ValueError: ip or domain or method is illegal.
        """
        if self.__check_ipv4():
            socket_af = usocket.AF_INET
        elif self.__check_ipv6():
            socket_af = usocket.AF_INET6
        else:
            raise ValueError("Args ip %s is illegal!" % self.__ip)

        if self.__method == 'TCP':
            socket_type = usocket.SOCK_STREAM
            socket_proto = usocket.IPPROTO_TCP
        elif self.__method == 'UDP':
            socket_type = usocket.SOCK_DGRAM
            socket_proto = usocket.IPPROTO_UDP
        else:
            raise ValueError("Args method is TCP or UDP, not %s" % self.__method)
        self.__socket_args = (socket_af, socket_type, socket_proto)

    def __check_ipv4(self):
        """Check ip is ipv4.

        Returns:
            bool: True - ip is ipv4, False - ip is not ipv4
        """
        self.__ipv4_item = r"(25[0-5]|2[0-4]\d|[01]?\d\d?)"
        self.__ipv4_regex = r"^{item}\.{item}\.{item}\.{item}$".format(item=self.__ipv4_item)
        if self.__ip.find(":") == -1:
            ipv4_re = ure.search(self.__ipv4_regex, self.__ip)
            if ipv4_re:
                if ipv4_re.group(0) == self.__ip:
                    return True
        return False

    def __check_ipv6(self):
        """Check ip is ipv6.

        Returns:
            bool: True - ip is ipv6, False - ip is not ipv6
        """
        # self.__ipv6_item = r"[0-9a-fA-F]{1:4}"
        self.__ipv6_code = r"[0-9a-fA-F]"
        ipv6_item_format = [self.__ipv6_code * i for i in range(1, 5)]
        self.__ipv6_item = r"{}|{}|{}|{}".format(*ipv6_item_format)

        # TODO: check ip is ipv6 by regex when ure support `{n,m}`
        # ipv4_regex = r"({item}\.{item}\.{item}\.{item})".format(item=self.__ipv4_item)
        # regex = r"""
        #     ^({ipv6}:){6}{ipv4}$|
        #     ^::({ipv6}:){0,4}{ipv4}$|
        #     ^({ipv6}:):({ipv6}:){0,3}{ipv4}$|
        #     ^({ipv6}:){2}:({ipv6}:){0,2}{ipv4}$|
        #     ^({ipv6}:){3}:({ipv6}:){0,1}{ipv4}$|
        #     ^({ipv6}:){4}:{ipv4}$|
        #     ^({ipv6}:){7}{ipv6}$|^:((:{ipv6}){1,6}|:)$|
        #     ^{ipv6}:((:{ipv6}){1,5}|:)$|
        #     ^({ipv6}:){2}((:{ipv6}){1,4}|:)$|
        #     ^({ipv6}:){3}((:{ipv6}){1,3}|:)$|
        #     ^({ipv6}:){4}((:{ipv6}){1,2}|:)$|
        #     ^({ipv6}:){5}:({ipv6})?$|
        #     ^({ipv6}:){6}:$
        # """.format(ipv4=ipv4_regex, ipv6=self.__ipv6_item)

        if self.ip.startswith("::") or ure.search(self.__ipv6_item + ":", self.__ip):
            return True
        else:
            return False

    @option_lock(_socket_lock)
    def __connect(self):
        """Socket connect when method is TCP

        Returns:
            bool: True - success, False - falied
        """
        if self.__socket_args:
            try:
                self.__socket = usocket.socket(*self.__socket_args)
                if self.__method == 'TCP':
                    self.__socket.connect(self.__addr)
                return True
            except Exception as e:
                usys.print_exception(e)

        return False

    @option_lock(_socket_lock)
    def __disconnect(self):
        """Socket disconnect

        Returns:
            bool: True - success, False - falied
        """
        if self.__socket is not None:
            try:
                self.__socket.close()
                self.__socket = None
                return True
            except Exception as e:
                usys.print_exception(e)
                return False
        else:
            return True

    @option_lock(_socket_lock)
    def __send(self, data):
        """Send data by socket.

        Args:
            data(bytes): byte stream

        Returns:
            bool: True - success, False - falied.
        """
        if self.__socket is not None:
            try:
                if self.__method == "TCP":
                    write_data_num = self.__socket.write(data)
                    log.debug("socket.write data: %s, write_data_num: %s" % (str(data), write_data_num))
                    if write_data_num == len(data):
                        return True
                elif self.__method == "UDP":
                    send_data_num = self.__socket.sendto(data, self.__addr)
                    if send_data_num == len(data):
                        return True
            except Exception as e:
                usys.print_exception(e)

        return False

    def __read(self, bufsize=1024):
        """Read data by socket.

        Args:
            bufsize(int): read data size.

        Returns:
            bytes: read data info
        """
        log.debug("start read")
        data = b""
        if self.__socket is not None:
            try:
                while True:
                    if data:
                        self.__socket.settimeout(0.5)
                    else:
                        self.__socket.settimeout(self.__timeout)
                    read_data = self.__socket.recv(bufsize)
                    log.debug("read_data: %s" % read_data)
                    if read_data:
                        data += read_data
                    else:
                        break
            except Exception as e:
                if e.args[0] != 110:
                    usys.print_exception(e)
                    log.error("%s read falied. error: %s" % (self.__method, str(e)))

        return data

    def _downlink_thread_start(self):
        """This function starts a thread to read the data sent by the server"""
        pass

    def _downlink_thread_stop(self):
        """This function stop the thread that read the data sent by the server"""
        pass

    def _heart_beat_timer_start(self):
        """This function starts a timer to send heart beat to server"""
        pass

    def _heart_beat_timer_stop(self):
        """This function stop the timer that send heart beat to server"""
        pass

    def status(self):
        """Get socket connection status

        Returns:
            [int]:
                -1: Error
                 0: Connected
                 1: Connecting
                 2: Disconnect
        """
        _status = -1
        if self.__socket is not None:
            try:
                if self.__method == "TCP":
                    socket_sta = self.__socket.getsocketsta()
                    log.debug("socket.getsocketsta(): %s" % socket_sta)
                    if socket_sta in range(4):
                        # Connecting
                        _status = 1
                    elif socket_sta == 4:
                        # Connected
                        _status = 0
                    elif socket_sta in range(5, 11):
                        # Disconnect
                        _status = 2
                elif self.__method == "UDP":
                    _status = 0
            except Exception as e:
                usys.print_exception(e)
                log.error(str(e))

        return _status

    def connect(self):
        """Connect server and start downlink thread for server

        Returns:
            bool: True - success, False - failed
        """
        if self.__connect():
            self._downlink_thread_start()
            return True

        return False

    def disconnect(self):
        """Disconnect server, than stop downlink thread and heart beat timer

        Returns:
            bool: True - success, False - failed
        """
        if self.__disconnect():
            self._heart_beat_timer_stop()
            self._downlink_thread_stop()
            return True

        return False
