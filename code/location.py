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
import utime
import osTimer
import _thread
import cellLocator

from queue import Queue
from machine import UART
from wifilocator import wifilocator

from usr.logging import getLogger
from usr.common import Singleton
from usr.common import option_lock

try:
    import quecgnss
except ImportError:
    quecgnss = None

log = getLogger(__name__)

_gps_read_lock = _thread.allocate_lock()


class _loc_method(object):
    none = 0x0
    gps = 0x1
    cell = 0x2
    wifi = 0x4
    all = 0x7


class _gps_mode(object):
    none = 0x0
    internal = 0x1
    external = 0x2


class GPSParsing(object):

    def read_GxRMC(self, gps_data):
        rmc_re = ure.search(
            r"\$G[NP]RMC,\d+\.\d+,[AV],\d+\.\d+,[NS],\d+\.\d+,[EW],\d+\.\d+,\d+\.\d+,\d+,\d*\.*\d*,[EW]*,[ADEN]*,[SCUV]*\**(\d|\w)*",
            gps_data)
        if rmc_re:
            return rmc_re.group(0)
        return ""

    def read_GxGGA(self, gps_data):
        gga_re = ure.search(
            r"\$G[BLPN]GGA,\d+\.\d+,\d+\.\d+,[NS],\d+\.\d+,[EW],[0126],\d+,\d+\.\d+,-*\d+\.\d+,M,-*\d+\.\d+,M,\d*,\**(\d|\w)*",
            gps_data)
        if gga_re:
            return gga_re.group(0)
        return ""

    def read_GxGGA_satellite_num(self, gps_data):
        gga_data = self.read_GxGGA(gps_data)
        if gga_data:
            satellite_num_re = ure.search(r",[EW],[0126],\d+,", gga_data)
            if satellite_num_re:
                return satellite_num_re.group(0).split(",")[-2]
        return ""

    def read_GxVTG(self, gps_data):
        vtg_re = ure.search(r"\$G[NP]VTG,\d+\.\d+,T,\d*\.*\d*,M,\d+\.\d+,N,\d+\.\d+,K,[ADEN]*\*(\d|\w)*", gps_data)
        if vtg_re:
            return vtg_re.group(0)
        return ""

    def read_GxVTG_speed(self, gps_data):
        vtg_data = self.read_GxVTG(gps_data)
        if vtg_data:
            speed_re = ure.search(r",N,\d+\.\d+,K,", vtg_data)
            if speed_re:
                return speed_re.group(0)[3:-3]
        return ""

    def read_GxGSV(self, gps_data):
        gsv_re = ure.search(r"\$G[NP]GSV,\d+,\d+,\d+,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*\**(\d|\w)*", gps_data)
        if gsv_re:
            return gsv_re.group(0)

        return ""

    def read_GxGSV_satellite_num(self, gps_data):
        gsv_data = self.read_GxGSV(gps_data)
        if gsv_data:
            satellite_num_re = ure.search(r"\$G[NP]GSV,\d+,\d+,\d+,", gsv_data)
            if satellite_num_re:
                return satellite_num_re.group(0).split(",")[-2]
        return ""


class GPS(Singleton):
    def __init__(self, gps_cfg, gps_mode):
        self.gps_cfg = gps_cfg
        self.gps_mode = gps_mode
        self.uart_obj = None
        self.gnss_obj = quecgnss
        self.gps_parsing = GPSParsing()

        self.__uart_retrieve_queue = None
        self.__first_break = 0
        self.__second_break = 0
        self.__gps_timer = osTimer()

        if self.gps_mode & _gps_mode.external:
            self._uart_init()
        elif self.gps_mode & _gps_mode.internal:
            self._gnss_init()

    def _uart_init(self):
        self.__uart_retrieve_queue = Queue(maxsize=8)
        self._uart_open()

    def _uart_open(self):
        self.uart_obj = UART(
            self.gps_cfg["UARTn"], self.gps_cfg["buadrate"], self.gps_cfg["databits"],
            self.gps_cfg["parity"], self.gps_cfg["stopbits"], self.gps_cfg["flowctl"]
        )
        self.uart_obj.set_callback(self._uart_retrieve_cb)

    def _uart_close(self):
        self.uart_obj.close()

    def _uart_retrieve_cb(self, args):
        """
        GPS data retrieve callback from UART
        When data comes, send a message to queue of data length
        """
        toRead = args[2]
        log.debug("GPS _uart_retrieve_cb args: %s" % str(args))
        if toRead:
            if self.__uart_retrieve_queue.size() >= 8:
                self.__uart_retrieve_queue.get()
            self.__uart_retrieve_queue.put(toRead)

    def _gnss_init(self):
        if self.gnss_obj:
            if self.gnss_obj.init() != 0:
                self._gnss_open()
                log.error("GNSS INIT Failed.")
            else:
                log.debug("GNSS INIT Success.")
        else:
            log.error("Module quecgnss Import Error.")

    def _gnss_open(self):
        if self.gnss_obj.get_state() == 0:
            self.gnss_obj.gnssEnable(1)

    def _gnss_close(self):
        self.gnss_obj.gnssEnable(0)

    def _first_gps_timer_callback(self, args):
        self.__first_break = 1
        if self.__uart_retrieve_queue is not None:
            self.__uart_retrieve_queue.put(0)

    def _second_gps_timer_callback(self, args):
        self.__second_break = 1
        if self.__uart_retrieve_queue is not None:
            self.__uart_retrieve_queue.put(0)

    def _uart_read(self):
        self._uart_open()
        log.debug("_uart_read start")

        while self.__first_break == 0:
            self.__gps_timer.start(50, 0, self._first_gps_timer_callback)
            nread = self.__uart_retrieve_queue.get()
            log.debug("__first_break nread: %s" % nread)
            data = self.uart_obj.read(nread).decode()
            self.__gps_timer.stop()
        self.__first_break = 0

        data = ""
        rmc_data = ""
        gga_data = ""
        vtg_data = ""
        gsv_data = ""
        while self.__second_break == 0:
            get_flag = False
            self.__gps_timer.start(1500, 0, self._second_gps_timer_callback)
            nread = self.__uart_retrieve_queue.get()
            log.debug("__second_break nread: %s" % nread)
            if nread:
                if not rmc_data:
                    rmc_data = self.gps_parsing.read_GxRMC(data)
                    get_flag = True
                if not gga_data:
                    gga_data = self.gps_parsing.read_GxGGA(data)
                    get_flag = True
                if not vtg_data:
                    vtg_data = self.gps_parsing.read_GxVTG(data)
                    get_flag = True
                if not gsv_data:
                    gsv_data = self.gps_parsing.read_GxGSV(data)
                    get_flag = True
                if get_flag:
                    data += self.uart_obj.read(nread).decode()
                if rmc_data and gga_data and vtg_data and gsv_data:
                    self.__second_break = 1
            self.__gps_timer.stop()
        log.debug("__second_break(_uart_read) data: %s" % data)
        self.__second_break = 0

        self._uart_close()
        return data

    def _quecgnss_read(self):
        self._gnss_init()

        while self.__first_break == 0:
            self.__gps_timer.start(50, 0, self._first_gps_timer_callback)
            data = quecgnss.read(1024)
            self.__gps_timer.stop()
        self.__first_break = 0

        data = ""
        rmc_data = ""
        gga_data = ""
        vtg_data = ""
        gsv_data = ""
        count = 0
        while self.__second_break == 0:
            get_flag = False
            self.__gps_timer.start(1500, 0, self._second_gps_timer_callback)
            gnss_data = quecgnss.read(1024)
            if gnss_data and gnss_data[1]:
                if not rmc_data:
                    rmc_data = self.gps_parsing.read_GxRMC(data)
                    get_flag = True
                if not gga_data:
                    gga_data = self.gps_parsing.read_GxGGA(data)
                    get_flag = True
                if not vtg_data:
                    vtg_data = self.gps_parsing.read_GxVTG(data)
                    get_flag = True
                if not gsv_data:
                    gsv_data = self.gps_parsing.read_GxGSV(data)
                    get_flag = True
                if get_flag:
                    data += gnss_data[1].decode() if len(gnss_data) > 1 and gnss_data[1] else ""
                if rmc_data and gga_data and vtg_data and gsv_data:
                    self.__second_break = 1
            self.__gps_timer.stop()

            if count > 5:
                self.__second_break = 1
            count += 1
            utime.sleep_ms(300)
        self.__second_break = 0

        self._gnss_close()
        return data

    @option_lock(_gps_read_lock)
    def read(self):
        res = -1
        gps_data = ""
        if self.gps_mode & _gps_mode.external:
            gps_data = self._uart_read()
        elif self.gps_mode & _gps_mode.internal:
            gps_data = self._quecgnss_read()

        # TODO: Disable Output Satellite Num:
        if gps_data:
            gga_satellite = self.gps_parsing.read_GxGGA_satellite_num(gps_data)
            log.debug("GxGGA Satellite Num %s" % gga_satellite)
            gsv_satellite = self.gps_parsing.read_GxGSV_satellite_num(gps_data)
            log.debug("GxGSV Satellite Num %s" % gsv_satellite)
            res = 0

        return (res, gps_data)

    def start(self):
        # TODO: Set GPS ON
        return True

    def stop(self):
        # TODO: Set GPS OFF
        return True


class CellLocator(object):
    def __init__(self, cellLocator_cfg):
        self.cellLocator_cfg = cellLocator_cfg

    def read(self):
        res = -1
        loc_data = cellLocator.getLocation(
            self.cellLocator_cfg["serverAddr"],
            self.cellLocator_cfg["port"],
            self.cellLocator_cfg["token"],
            self.cellLocator_cfg["timeout"],
            self.cellLocator_cfg["profileIdx"]
        )
        if isinstance(loc_data, tuple) and len(loc_data) == 3:
            res = 0
        else:
            res = loc_data
            loc_data = ()

        return (res, loc_data)


class WiFiLocator(object):
    def __init__(self, wifiLocator_cfg):
        self.wifilocator_obj = wifilocator(wifiLocator_cfg["token"])

    def read(self):
        res = -1
        loc_data = self.wifilocator_obj.getwifilocator()
        if isinstance(loc_data, tuple) and len(loc_data) == 3:
            res = 0
        else:
            res = loc_data
            loc_data = ()

        return (res, loc_data)


class Location(Singleton):
    gps = None
    cellLoc = None
    wifiLoc = None

    def __init__(self, gps_mode, locator_init_params):
        self.gps_mode = gps_mode
        self.locator_init_params = locator_init_params

    def __locater_init(self, loc_method):

        if loc_method & _loc_method.gps:
            if self.gps is None:
                if self.locator_init_params.get("gps_cfg"):
                    self.gps = GPS(self.locator_init_params["gps_cfg"], self.gps_mode)
                else:
                    raise ValueError("Invalid gps init parameters.")
        else:
            self.gps = None

        if loc_method & _loc_method.cell:
            if self.cellLoc is None:
                if self.locator_init_params.get("cellLocator_cfg"):
                    self.cellLoc = CellLocator(self.locator_init_params["cellLocator_cfg"])
                else:
                    raise ValueError("Invalid cell-locator init parameters.")
        else:
            self.cellLoc = None

        if loc_method & _loc_method.wifi:
            if self.wifiLoc is None:
                if self.locator_init_params.get("wifiLocator_cfg"):
                    self.wifiLoc = WiFiLocator(self.locator_init_params["wifiLocator_cfg"])
                else:
                    raise ValueError("Invalid wifi-locator init parameters.")
        else:
            self.wifiLoc = None

    def __read_gps(self):
        if self.gps:
            return self.gps.read()[1]
        return ""

    def __read_cell(self):
        if self.cellLoc:
            return self.cellLoc.read()[1]
        return ()

    def __read_wifi(self):
        if self.wifiLoc:
            return self.wifiLoc.read()[1]
        return ()

    def read(self, loc_method, read_all=False):
        """
        1. If read_all Is False
        1.1. Get GPS If loc_method Include GPS And GPS Data Exist;
        1.2. Get Cell If loc_method Inculde Cell And Not GPS Data;
        1.3. Get Wifi If loc_method Include Wifi And Not Cell Data;
        2. If read_all Is True, Return loc_method Include All Loc Method Data.

        Return Data Format:

        {
            1: "$GPGGA,XXX",
            2: (0.00, 0.00, 0.00),
            4: (0.00, 0.00, 0.00),
        }
        """
        loc_data = {}
        self.__locater_init(loc_method)

        if loc_method & _loc_method.gps:
            loc_data[_loc_method.gps] = self.__read_gps()
            if read_all is False:
                return loc_data

        if loc_method & _loc_method.cell:
            loc_data[_loc_method.cell] = self.__read_cell()
            if read_all is False:
                return loc_data

        if loc_method & _loc_method.wifi:
            loc_data[_loc_method.wifi] = self.__read_wifi()
            if read_all is False:
                return loc_data

        return loc_data
