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


class GPSMatch(object):

    def GxRMC(self, gps_data):
        rmc_re = ure.search(
            r"\$G[NP]RMC,\d+\.\d+,[AV],\d+\.\d+,[NS],\d+\.\d+,[EW],\d+\.\d+,\d+\.\d+,\d+,\d*\.*\d*,[EW]*,[ADEN]*,[SCUV]*\**(\d|\w)*",
            gps_data)
        if rmc_re:
            return rmc_re.group(0)
        return ""

    def GxGGA(self, gps_data):
        gga_re = ure.search(
            r"\$G[BLPN]GGA,\d+\.\d+,\d+\.\d+,[NS],\d+\.\d+,[EW],[0126],\d+,\d+\.\d+,-*\d+\.\d+,M,-*\d+\.\d+,M,\d*,\**(\d|\w)*",
            gps_data)
        if gga_re:
            return gga_re.group(0)
        return ""

    def GxVTG(self, gps_data):
        vtg_re = ure.search(r"\$G[NP]VTG,\d+\.\d+,T,\d*\.*\d*,M,\d+\.\d+,N,\d+\.\d+,K,[ADEN]*\*(\d|\w)*", gps_data)
        if vtg_re:
            return vtg_re.group(0)
        return ""

    def GxGSV(self, gps_data):
        gsv_re = ure.search(r"\$G[NP]GSV,\d+,\d+,\d+,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*\**(\d|\w)*", gps_data)
        if gsv_re:
            return gsv_re.group(0)

        return ""


class GPSParse(object):

    def GxGGA_satellite_num(self, gga_data):
        if gga_data:
            satellite_num_re = ure.search(r",[EW],[0126],\d+,", gga_data)
            if satellite_num_re:
                return satellite_num_re.group(0).split(",")[-2]
        return ""

    def GxVTG_speed(self, vtg_data):
        if vtg_data:
            speed_re = ure.search(r",N,\d+\.\d+,K,", vtg_data)
            if speed_re:
                return speed_re.group(0)[3:-3]
        return ""

    def GxGSV_satellite_num(self, gsv_data):
        if gsv_data:
            satellite_num_re = ure.search(r"\$G[NP]GSV,\d+,\d+,\d+,", gsv_data)
            if satellite_num_re:
                return satellite_num_re.group(0).split(",")[-2]
        return ""

    def GxGGA_latitude(self, gga_data):
        if gga_data:
            latitude_re = ure.search(r",[0-9]+\.[0-9]+,[NS],", gga_data)
            if latitude_re:
                return latitude_re.group(0)[1:-3]
        return ""

    def GxGGA_longtitude(self, gga_data):
        if gga_data:
            longtitude_re = ure.search(r",[0-9]+\.[0-9]+,[EW],", gga_data)
            if longtitude_re:
                return longtitude_re.group(0)[1:-3]
        return ""

    def GxGGA_altitude(self, gga_data):
        if gga_data:
            altitude_re = ure.search(r",-*[0-9]+\.[0-9]+,M,", gga_data)
            if altitude_re:
                return altitude_re.group(0)[1:-3]
        return ""


class GPS(Singleton):
    def __init__(self, gps_cfg, gps_mode):
        self.__gps_cfg = gps_cfg
        self.__gps_mode = gps_mode
        self.__external_obj = None
        self.__internal_obj = quecgnss
        self.__gps_match = GPSMatch()
        self.__gps_parse = GPSParse()

        self.__external_retrieve_queue = None
        self.__first_break = 0
        self.__break = 0
        self.__gps_data = ""
        self.__rmc_data = ""
        self.__gga_data = ""
        self.__vtg_data = ""
        self.__gsv_data = ""
        self.__gps_timer = osTimer()
        self.__gps_clean_timer = osTimer()

        if self.__gps_mode & _gps_mode.external:
            self.__external_init()
        elif self.__gps_mode & _gps_mode.internal:
            self.__internal_init()

    def __first_gps_timer_callback(self, args):
        self.__first_break = 1
        if self.__external_retrieve_queue is not None:
            self.__external_retrieve_queue.put(0)

    def __gps_timer_callback(self, args):
        self.__break = 1
        if self.__external_retrieve_queue is not None:
            self.__external_retrieve_queue.put(0)

    def __gps_clean_cb(self, args):
        if self.__break == 0:
            self.__gps_data = ""
            self.__rmc_data = ""
            self.__gga_data = ""
            self.__vtg_data = ""
            self.__gsv_data = ""

    def __external_init(self):
        self.__external_retrieve_queue = Queue(maxsize=8)
        self.__external_open()

    def __external_open(self):
        self.__external_obj = UART(
            self.__gps_cfg["UARTn"], self.__gps_cfg["buadrate"], self.__gps_cfg["databits"],
            self.__gps_cfg["parity"], self.__gps_cfg["stopbits"], self.__gps_cfg["flowctl"]
        )
        self.__external_obj.set_callback(self.__external_retrieve_cb)

    def __external_close(self):
        self.__external_obj.close()

    def __external_retrieve_cb(self, args):
        """
        GPS data retrieve callback from UART
        When data comes, send a message to queue of data length
        """
        toRead = args[2]
        log.debug("GPS __external_retrieve_cb args: %s" % str(args))
        if toRead:
            if self.__external_retrieve_queue.size() >= 8:
                self.__external_retrieve_queue.get()
            self.__external_retrieve_queue.put(toRead)

    def __internal_init(self):
        if self.__internal_obj:
            if self.__internal_obj.init() != 0:
                self.__insternal_open()
                log.error("GNSS INIT Failed.")
            else:
                log.debug("GNSS INIT Success.")
        else:
            log.error("Module quecgnss Import Error.")

    def __insternal_open(self):
        if self.__internal_obj.get_state() == 0:
            self.__internal_obj.gnssEnable(1)

    def __internal_close(self):
        self.__internal_obj.gnssEnable(0)

    @option_lock(_gps_read_lock)
    def __external_read(self):
        self.__external_open()
        log.debug("__external_read start")

        while self.__break == 0:
            self.__gps_timer.start(50, 0, self.__gps_timer_callback)
            nread = self.__external_retrieve_queue.get()
            log.debug("[first] nread: %s" % nread)
            self.__gps_data = self.__external_obj.read(nread).decode()
        self.__break = 0

        self.__gps_data = ""
        self.__rmc_data = ""
        self.__gga_data = ""
        self.__vtg_data = ""
        self.__gsv_data = ""
        self.__gps_clean_timer.start(1050, 1, self.__gps_clean_cb)
        while self.__break == 0:
            self.__gps_timer.start(1500, 0, self.__gps_timer_callback)
            nread = self.__external_retrieve_queue.get()
            log.debug("[second] nread: %s" % nread)
            if nread:
                self.__gps_data += self.__external_obj.read(nread).decode()
                if not self.__rmc_data:
                    self.__rmc_data = self.__gps_match.GxRMC(self.__gps_data)
                if not self.__gga_data:
                    self.__gga_data = self.__gps_match.GxGGA(self.__gps_data)
                if not self.__vtg_data:
                    self.__vtg_data = self.__gps_match.GxVTG(self.__gps_data)
                if not self.__gsv_data:
                    self.__gsv_data = self.__gps_match.GxGSV(self.__gps_data)
                if self.__rmc_data and self.__gga_data and self.__vtg_data and self.__gsv_data:
                    self.__break = 1
            self.__gps_timer.stop()
        self.__gps_clean_timer.stop()
        self.__break = 0

        self.__external_close()
        log.debug("__external_read data: %s" % self.__gps_data)
        return self.__gps_data

    @option_lock(_gps_read_lock)
    def __internal_read(self):
        self.__external_open()

        while self.__break == 0:
            self.__gps_timer.start(50, 0, self.__gps_timer_callback)
            self.__gps_data = quecgnss.read(1024)
            self.__gps_timer.stop()
        self.__break = 0

        self.__gps_data = ""
        self.__rmc_data = ""
        self.__gga_data = ""
        self.__vtg_data = ""
        self.__gsv_data = ""
        self.__gps_clean_timer.start(1050, 1, self.__gps_clean_cb)
        while self.__break == 0:
            self.__gps_timer.start(1500, 0, self.__gps_timer_callback)
            gnss_data = quecgnss.read(1024)
            if gnss_data and gnss_data[1]:
                self.__gps_data += gnss_data[1].decode() if len(gnss_data) > 1 and gnss_data[1] else ""
                if not self.__rmc_data:
                    self.__rmc_data = self.__gps_match.GxRMC(self.__gps_data)
                if not self.__gga_data:
                    self.__gga_data = self.__gps_match.GxGGA(self.__gps_data)
                if not self.__vtg_data:
                    self.__vtg_data = self.__gps_match.GxVTG(self.__gps_data)
                if not self.__gsv_data:
                    self.__gsv_data = self.__gps_match.GxGSV(self.__gps_data)
                if self.__rmc_data and self.__gga_data and self.__vtg_data and self.__gsv_data:
                    self.__break = 1
            self.__gps_timer.stop()
        self.__gps_clean_timer.stop()
        self.__break = 0

        self.__internal_close()
        return self.__gps_data

    def read(self):
        res = -1
        gps_data = ""
        if self.__gps_mode & _gps_mode.external:
            gps_data = self.__external_read()
        elif self.__gps_mode & _gps_mode.internal:
            gps_data = self.__internal_read()

        # TODO: Disable Output Satellite Num:
        if gps_data:
            gga_satellite = self.__gps_parse.GxGGA_satellite_num(self.__gps_match.GxGGA(gps_data))
            log.debug("GxGGA Satellite Num %s" % gga_satellite)
            gsv_satellite = self.__gps_parse.GxGSV_satellite_num(self.__gps_match.GxGSV(gps_data))
            log.debug("GxGSV Satellite Num %s" % gsv_satellite)
            res = 0

        return (res, gps_data)

    def read_latitude(self, gps_data):
        return self.__gps_parse.GxGGA_latitude(self.__gps_match.GxGGA(gps_data))

    def read_longtitude(self, gps_data):
        return self.__gps_parse.GxGGA_longtitude(self.__gps_match.GxGGA(gps_data))

    def read_altitude(self, gps_data):
        return self.__gps_parse.GxGGA_altitude(self.__gps_match.GxGGA(gps_data))

    def on(self):
        # TODO: Set GPS ON
        return True

    def off(self):
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
        self.__gps_mode = gps_mode
        self.locator_init_params = locator_init_params

    def __locater_init(self, loc_method):

        if loc_method & _loc_method.gps:
            if self.gps is None:
                if self.locator_init_params.get("gps_cfg"):
                    self.gps = GPS(self.locator_init_params["gps_cfg"], self.__gps_mode)
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

    def read(self, loc_method):
        """
        1. If loc_method include gps then get gps data;
        2. If loc_method inculde cell then get cell data;
        3. If loc_method Include wifi then get wifi data;

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

        if loc_method & _loc_method.cell:
            loc_data[_loc_method.cell] = self.__read_cell()

        if loc_method & _loc_method.wifi:
            loc_data[_loc_method.wifi] = self.__read_wifi()

        return loc_data
