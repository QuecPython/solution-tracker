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
    gps = 0x1
    cell = 0x2
    wifi = 0x4


class _gps_mode(object):
    none = 0x0
    internal = 0x1
    external = 0x2


class GPSMatch(object):
    """This class is match gps NEMA 0183"""

    def GxRMC(self, gps_data):
        """Match Recommended Minimum Specific GPS/TRANSIT Data（RMC）"""
        if gps_data:
            rmc_re = ure.search(
                r"\$G[NP]RMC,\d+\.\d+,[AV],\d+\.\d+,[NS],\d+\.\d+,[EW],\d+\.\d+,\d+\.\d+,\d+,\d*\.*\d*,[EW]*,[ADEN]*,[SCUV]*\**(\d|\w)*",
                gps_data)
            if rmc_re:
                return rmc_re.group(0)
        return ""

    def GxGGA(self, gps_data):
        """Match Global Positioning System Fix Data（GGA）"""
        if gps_data:
            gga_re = ure.search(
                r"\$G[BLPN]GGA,\d+\.\d+,\d+\.\d+,[NS],\d+\.\d+,[EW],[0126],\d+,\d+\.\d+,-*\d+\.\d+,M,-*\d+\.\d+,M,\d*,\**(\d|\w)*",
                gps_data)
            if gga_re:
                return gga_re.group(0)
        return ""

    def GxVTG(self, gps_data):
        """Match Track Made Good and Ground Speed（VTG）"""
        if gps_data:
            vtg_re = ure.search(r"\$G[NP]VTG,\d+\.\d+,T,\d*\.*\d*,M,\d+\.\d+,N,\d+\.\d+,K,[ADEN]*\*(\d|\w)*", gps_data)
            if vtg_re:
                return vtg_re.group(0)
        return ""

    def GxGSV(self, gps_data):
        """Mactch GPS Satellites in View（GSV）"""
        if gps_data:
            gsv_re = ure.search(r"\$G[NP]GSV,\d+,\d+,\d+,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*,\d*\**(\d|\w)*", gps_data)
            if gsv_re:
                return gsv_re.group(0)
        return ""


class GPSParse(object):
    """Parse details from gps data"""

    def GxGGA_satellite_num(self, gga_data):
        """Parse satellite num from GGA"""
        if gga_data:
            satellite_num_re = ure.search(r",[EW],[0126],\d+,", gga_data)
            if satellite_num_re:
                return satellite_num_re.group(0).split(",")[-2]
        return ""

    def GxVTG_speed(self, vtg_data):
        """Parse speed from VTG"""
        if vtg_data:
            speed_re = ure.search(r",N,\d+\.\d+,K,", vtg_data)
            if speed_re:
                return speed_re.group(0)[3:-3]
        return ""

    def GxGSV_satellite_num(self, gsv_data):
        """Parse satellite num from GSV"""
        if gsv_data:
            satellite_num_re = ure.search(r"\$G[NP]GSV,\d+,\d+,\d+,", gsv_data)
            if satellite_num_re:
                return satellite_num_re.group(0).split(",")[-2]
        return ""

    def GxGGA_latitude(self, gga_data):
        """Parse latitude from GGA"""
        if gga_data:
            latitude_re = ure.search(r",[0-9]+\.[0-9]+,[NS],", gga_data)
            if latitude_re:
                return latitude_re.group(0)[1:-3]
        return ""

    def GxGGA_longtitude(self, gga_data):
        """Parse longtitude from GGA"""
        if gga_data:
            longtitude_re = ure.search(r",[0-9]+\.[0-9]+,[EW],", gga_data)
            if longtitude_re:
                return longtitude_re.group(0)[1:-3]
        return ""

    def GxGGA_altitude(self, gga_data):
        """Parse altitude from GGA"""
        if gga_data:
            altitude_re = ure.search(r",-*[0-9]+\.[0-9]+,M,", gga_data)
            if altitude_re:
                return altitude_re.group(0)[1:-3]
        return ""


class GPS(Singleton):
    """This class if for reading gps data.

    Now support external gps and internal gps.
    """

    def __init__(self, gps_cfg, gps_mode):
        """ Init gps params

        Parameter:
            gps_cfg: this is uart init params for external gps
            gps_mode: `internal` or `external`

        """
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

    def __gps_timer_callback(self, args):
        """GPS read timer callback
        When over time to get uart data, break queue wait
        """
        self.__break = 1
        if self.__external_retrieve_queue is not None:
            self.__external_retrieve_queue.put(0)

    def __gps_clean_callback(self, args):
        """GPS read old data clean timer callback
        When GPS read over time, clean old gps data, wait to read new gps data.
        """
        if self.__break == 0:
            self.__gps_data = ""
            self.__rmc_data = ""
            self.__gga_data = ""
            self.__vtg_data = ""
            self.__gsv_data = ""

    def __external_init(self):
        """External GPS init"""
        self.__external_retrieve_queue = Queue(maxsize=8)
        self.__external_open()

    def __external_open(self):
        """External GPS start, UART init"""
        self.__external_obj = UART(
            self.__gps_cfg["UARTn"], self.__gps_cfg["buadrate"], self.__gps_cfg["databits"],
            self.__gps_cfg["parity"], self.__gps_cfg["stopbits"], self.__gps_cfg["flowctl"]
        )
        self.__external_obj.set_callback(self.__external_retrieve_cb)

    def __external_close(self):
        """External GPS close, UART close, NOT GPS stop"""
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
        """Internal GPS init"""
        if self.__internal_obj:
            if self.__internal_obj.init() != 0:
                self.__insternal_open()
                log.error("GNSS INIT Failed.")
            else:
                log.debug("GNSS INIT Success.")
        else:
            log.error("Module quecgnss Import Error.")

    def __insternal_open(self):
        """Internal GPS enable"""
        if self.__internal_obj.get_state() == 0:
            self.__internal_obj.gnssEnable(1)

    def __internal_close(self):
        """Internal GPS close"""
        self.__internal_obj.gnssEnable(0)

    @option_lock(_gps_read_lock)
    def __external_read(self):
        """Read external GPS data

        Return:
            $GPTXT,01,01,02,ANTSTATUS=OPEN*2B
            $GNRMC,073144.000,A,3149.330773,N,11706.946971,E,0.00,337.47,150422,,,D,V*07
            $GNVTG,337.47,T,,M,0.00,N,0.00,K,D*22
            $GNGGA,073144.000,3149.330773,N,11706.946971,E,2,19,0.66,85.161,M,-0.335,M,,*56
            $GNGSA,A,3,01,195,06,03,21,194,19,17,30,14,,,0.94,0.66,0.66,1*02
            $GNGSA,A,3,13,26,07,10,24,25,08,03,22,,,,0.94,0.66,0.66,4*03
            $GPGSV,3,1,12,14,84,210,31,195,67,057,46,17,52,328,28,50,51,161,33,1*54
            $GPGSV,3,2,12,194,49,157,33,03,48,090,37,19,36,305,32,06,34,242,32,1*58
            $GPGSV,3,3,12,01,32,041,35,30,17,204,22,21,07,051,13,07,03,183,,1*6B
            $BDGSV,5,1,18,07,86,063,30,10,75,322,30,08,60,211,34,03,52,192,33,1*71
            $BDGSV,5,2,18,24,44,276,33,13,43,215,33,01,43,135,30,26,40,208,37,1*71
            $BDGSV,5,3,18,02,38,230,,04,32,119,,22,26,135,30,19,25,076,,1*70
            $BDGSV,5,4,18,05,17,251,,25,06,322,27,09,02,211,22,21,02,179,,1*78
            $BDGSV,5,5,18,29,02,075,,20,01,035,,1*72
            $GNGLL,3149.330773,N,11706.946971,E,073144.000,A,D*4E
        """
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
        self.__gps_clean_timer.start(1050, 1, self.__gps_clean_callback)
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
        """Read internal GPS data

        Return:
            $GPTXT,01,01,02,ANTSTATUS=OPEN*2B
            $GNRMC,073144.000,A,3149.330773,N,11706.946971,E,0.00,337.47,150422,,,D,V*07
            $GNVTG,337.47,T,,M,0.00,N,0.00,K,D*22
            $GNGGA,073144.000,3149.330773,N,11706.946971,E,2,19,0.66,85.161,M,-0.335,M,,*56
            $GNGSA,A,3,01,195,06,03,21,194,19,17,30,14,,,0.94,0.66,0.66,1*02
            $GNGSA,A,3,13,26,07,10,24,25,08,03,22,,,,0.94,0.66,0.66,4*03
            $GPGSV,3,1,12,14,84,210,31,195,67,057,46,17,52,328,28,50,51,161,33,1*54
            $GPGSV,3,2,12,194,49,157,33,03,48,090,37,19,36,305,32,06,34,242,32,1*58
            $GPGSV,3,3,12,01,32,041,35,30,17,204,22,21,07,051,13,07,03,183,,1*6B
            $BDGSV,5,1,18,07,86,063,30,10,75,322,30,08,60,211,34,03,52,192,33,1*71
            $BDGSV,5,2,18,24,44,276,33,13,43,215,33,01,43,135,30,26,40,208,37,1*71
            $BDGSV,5,3,18,02,38,230,,04,32,119,,22,26,135,30,19,25,076,,1*70
            $BDGSV,5,4,18,05,17,251,,25,06,322,27,09,02,211,22,21,02,179,,1*78
            $BDGSV,5,5,18,29,02,075,,20,01,035,,1*72
            $GNGLL,3149.330773,N,11706.946971,E,073144.000,A,D*4E
        """
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
        self.__gps_clean_timer.start(1050, 1, self.__gps_clean_callback)
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
        """For user to read gps data

        Return: (res_code, gps_data)
            res_code:
                -  0: Success
                - -1: Failed
            gps_data:
                $GPTXT,01,01,02,ANTSTATUS=OPEN*2B
                $GNRMC,073144.000,A,3149.330773,N,11706.946971,E,0.00,337.47,150422,,,D,V*07
                $GNVTG,337.47,T,,M,0.00,N,0.00,K,D*22
                $GNGGA,073144.000,3149.330773,N,11706.946971,E,2,19,0.66,85.161,M,-0.335,M,,*56
                $GNGSA,A,3,01,195,06,03,21,194,19,17,30,14,,,0.94,0.66,0.66,1*02
                $GNGSA,A,3,13,26,07,10,24,25,08,03,22,,,,0.94,0.66,0.66,4*03
                $GPGSV,3,1,12,14,84,210,31,195,67,057,46,17,52,328,28,50,51,161,33,1*54
                $GPGSV,3,2,12,194,49,157,33,03,48,090,37,19,36,305,32,06,34,242,32,1*58
                $GPGSV,3,3,12,01,32,041,35,30,17,204,22,21,07,051,13,07,03,183,,1*6B
                $BDGSV,5,1,18,07,86,063,30,10,75,322,30,08,60,211,34,03,52,192,33,1*71
                $BDGSV,5,2,18,24,44,276,33,13,43,215,33,01,43,135,30,26,40,208,37,1*71
                $BDGSV,5,3,18,02,38,230,,04,32,119,,22,26,135,30,19,25,076,,1*70
                $BDGSV,5,4,18,05,17,251,,25,06,322,27,09,02,211,22,21,02,179,,1*78
                $BDGSV,5,5,18,29,02,075,,20,01,035,,1*72
                $GNGLL,3149.330773,N,11706.946971,E,073144.000,A,D*4E
        """
        gps_data = ""
        if self.__gps_mode & _gps_mode.external:
            gps_data = self.__external_read()
        elif self.__gps_mode & _gps_mode.internal:
            gps_data = self.__internal_read()

        res = 0 if gps_data else -1
        return (res, gps_data)

    def read_latitude(self, gps_data):
        """Read latitude from gps data"""
        return self.__gps_parse.GxGGA_latitude(self.__gps_match.GxGGA(gps_data))

    def read_longtitude(self, gps_data):
        """Read longtitude from gps data"""
        return self.__gps_parse.GxGGA_longtitude(self.__gps_match.GxGGA(gps_data))

    def read_altitude(self, gps_data):
        """Read altitude from gps data"""
        return self.__gps_parse.GxGGA_altitude(self.__gps_match.GxGGA(gps_data))

    def on(self):
        """GPS Module switch on"""
        # TODO: Set GPS ON
        return True

    def off(self):
        """GPS Module switch off"""
        # TODO: Set GPS OFF
        return True


class CellLocator(object):
    """This class is for reading cell location data"""

    def __init__(self, cell_cfg):
        self.cell_cfg = cell_cfg

    def read(self):
        """Read cell location data.

        Return: (res_code, loc_data)
            res_code:
                -  0: Success
                - -1: Initialization failed
                - -2: The server address is too long (more than 255 bytes)
                - -3: Wrong key length, must be 16 bytes
                - -4: The timeout period is out of range, the supported range is (1 ~ 300) s
                - -5: The specified PDP network is not connected, please confirm whether the PDP is correct
                - -6: Error getting coordinates
            loc_data:
                (117.1138, 31.82279, 550)
        """
        res = -1
        loc_data = cellLocator.getLocation(
            self.cell_cfg["serverAddr"],
            self.cell_cfg["port"],
            self.cell_cfg["token"],
            self.cell_cfg["timeout"],
            self.cell_cfg["profileIdx"]
        )
        if isinstance(loc_data, tuple) and len(loc_data) == 3:
            res = 0
        else:
            res = loc_data
            loc_data = ()

        return (res, loc_data)


class WiFiLocator(object):
    """This class is for reading wifi location data"""

    def __init__(self, wifi_cfg):
        self.wifilocator_obj = wifilocator(wifi_cfg["token"])

    def read(self):
        """Read wifi location data.

        Return: (res_code, loc_data)
            res_code:
                -  0: Success
                - -1: The current network is abnormal, please confirm whether the dial-up is normal
                - -2: Wrong key length, must be 16 bytes
                - -3: Error getting coordinates
            loc_data:
                (117.1138, 31.82279, 550)
        """
        res = -1
        loc_data = self.wifilocator_obj.getwifilocator()
        if isinstance(loc_data, tuple) and len(loc_data) == 3:
            res = 0
        else:
            res = loc_data
            loc_data = ()

        return (res, loc_data)


class Location(Singleton):
    """This class is for reading location data from gps, cell, wifi"""
    gps = None
    cellLoc = None
    wifiLoc = None

    def __init__(self, gps_mode, locator_init_params):
        self.__gps_mode = gps_mode
        self.__locator_init_params = locator_init_params

    def __locater_init(self, loc_method):
        """Init gps, cell, wifi by loc_method

        Parameter:
            loc_method:
                - 1: gps
                - 2: cell
                - 3: cell & gps
                - 4: wifi
                - 5: wifi & gps
                - 6: wifi & cell
                - 7: wifi & cell & gps
        """

        if loc_method & _loc_method.gps:
            if self.gps is None:
                if self.__locator_init_params.get("gps_cfg"):
                    self.gps = GPS(self.__locator_init_params["gps_cfg"], self.__gps_mode)
                else:
                    raise ValueError("Invalid gps init parameters.")
        else:
            self.gps = None

        if loc_method & _loc_method.cell:
            if self.cellLoc is None:
                if self.__locator_init_params.get("cell_cfg"):
                    self.cellLoc = CellLocator(self.__locator_init_params["cell_cfg"])
                else:
                    raise ValueError("Invalid cell-locator init parameters.")
        else:
            self.cellLoc = None

        if loc_method & _loc_method.wifi:
            if self.wifiLoc is None:
                if self.__locator_init_params.get("wifi_cfg"):
                    self.wifiLoc = WiFiLocator(self.__locator_init_params["wifi_cfg"])
                else:
                    raise ValueError("Invalid wifi-locator init parameters.")
        else:
            self.wifiLoc = None

    def __read_gps(self):
        """Read loction data from gps module

        Return:
            $GPTXT,01,01,02,ANTSTATUS=OPEN*2B
            $GNRMC,073144.000,A,3149.330773,N,11706.946971,E,0.00,337.47,150422,,,D,V*07
            $GNVTG,337.47,T,,M,0.00,N,0.00,K,D*22
            $GNGGA,073144.000,3149.330773,N,11706.946971,E,2,19,0.66,85.161,M,-0.335,M,,*56
            $GNGSA,A,3,01,195,06,03,21,194,19,17,30,14,,,0.94,0.66,0.66,1*02
            $GNGSA,A,3,13,26,07,10,24,25,08,03,22,,,,0.94,0.66,0.66,4*03
            $GPGSV,3,1,12,14,84,210,31,195,67,057,46,17,52,328,28,50,51,161,33,1*54
            $GPGSV,3,2,12,194,49,157,33,03,48,090,37,19,36,305,32,06,34,242,32,1*58
            $GPGSV,3,3,12,01,32,041,35,30,17,204,22,21,07,051,13,07,03,183,,1*6B
            $BDGSV,5,1,18,07,86,063,30,10,75,322,30,08,60,211,34,03,52,192,33,1*71
            $BDGSV,5,2,18,24,44,276,33,13,43,215,33,01,43,135,30,26,40,208,37,1*71
            $BDGSV,5,3,18,02,38,230,,04,32,119,,22,26,135,30,19,25,076,,1*70
            $BDGSV,5,4,18,05,17,251,,25,06,322,27,09,02,211,22,21,02,179,,1*78
            $BDGSV,5,5,18,29,02,075,,20,01,035,,1*72
            $GNGLL,3149.330773,N,11706.946971,E,073144.000,A,D*4E
        """
        if self.gps:
            return self.gps.read()[1]
        return ""

    def __read_cell(self):
        """Read loction data from cell module

        Return:
            (117.1138, 31.82279, 550) or ()
        """
        if self.cellLoc:
            return self.cellLoc.read()[1]
        return ()

    def __read_wifi(self):
        """Read loction data from wifi module

        Return:
            (117.1138, 31.82279, 550) or ()
        """
        if self.wifiLoc:
            return self.wifiLoc.read()[1]
        return ()

    def read(self, loc_method):
        """Read location data by loc_method
        1. If loc_method include gps then get gps data;
        2. If loc_method inculde cell then get cell data;
        3. If loc_method Include wifi then get wifi data;

        Parameter:
            loc_method:
                - 1: gps
                - 2: cell
                - 3: cell & gps
                - 4: wifi
                - 5: wifi & gps
                - 6: wifi & cell
                - 7: wifi & cell & gps

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
