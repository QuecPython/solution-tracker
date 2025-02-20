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

"""
@file      :_main.py
@author    :Jack Sun (jack.sun@quectel.com)
@brief     :Project start.
@version   :2.2.0
@date      :2022-10-31 14:42:25
@copyright :Copyright (c) 2022
"""

import _thread
try:
    from modules.battery import Battery
    from modules.history import History
    from modules.logging import getLogger
    from modules.net_manage import NetManager
    from modules.thingsboard import TBDeviceMQTTClient
    from modules.power_manage import PowerManage
    from modules.aliIot import AliIot, AliIotOTA
    from modules.location import GNSS, CellLocator, WiFiLocator, CoordinateSystemConvert
    from settings_user import UserConfig
    from tracker_tb import Tracker as TBTracker
    from tracker_ali import Tracker as AliTracker
    from settings import Settings, PROJECT_NAME, PROJECT_VERSION, FIRMWARE_NAME, FIRMWARE_VERSION
except ImportError:
    from usr.modules.battery import Battery
    from usr.modules.history import History
    from usr.modules.logging import getLogger
    from usr.modules.net_manage import NetManager
    from usr.modules.thingsboard import TBDeviceMQTTClient
    from usr.modules.power_manage import PowerManage
    from usr.modules.aliIot import AliIot, AliIotOTA
    from usr.modules.location import GNSS, CellLocator, WiFiLocator, CoordinateSystemConvert
    from usr.settings_user import UserConfig
    from usr.tracker_tb import Tracker as TBTracker
    from usr.tracker_ali import Tracker as AliTracker
    from usr.settings import Settings, PROJECT_NAME, PROJECT_VERSION, FIRMWARE_NAME, FIRMWARE_VERSION

log = getLogger(__name__)

def main():
    log.debug("[x] Main start.")
    log.info("PROJECT_NAME: %s, PROJECT_VERSION: %s" % (PROJECT_NAME, PROJECT_VERSION))
    log.info("DEVICE_FIRMWARE_NAME: %s, DEVICE_FIRMWARE_VERSION: %s" % (FIRMWARE_NAME, FIRMWARE_VERSION))

    # Init settings.
    settings = Settings()
    # Init battery.
    battery = Battery()
    # Init history
    history = History()
    # Init power manage and set device low energy.
    power_manage = PowerManage()
    power_manage.autosleep(1)
    # Init net modules and start net connect.
    net_manager = NetManager()
    _thread.stack_size(0x1000)
    _thread.start_new_thread(net_manager.net_connect, ())
    # Init GNSS modules and start reading and parsing gnss data.
    loc_cfg = settings.read("loc")
    gnss = GNSS(**loc_cfg["gps_cfg"])
    gnss.set_trans(0)
    gnss.start()
    # Init cell and wifi location modules.
    cell = CellLocator(**loc_cfg["cell_cfg"])
    wifi = WiFiLocator(**loc_cfg["wifi_cfg"])
    cyc = CoordinateSystemConvert()
    # Init tracker business modules.
    user_cfg = settings.read("user")
    server_cfg = settings.read("server")
    # Init coordinate system convert modules.
    if user_cfg["server"] == UserConfig._server.AliIot:
        server = AliIot(**server_cfg)
        server_ota = AliIotOTA(PROJECT_NAME, FIRMWARE_NAME)
        server_ota.set_server(server)
        tracker = AliTracker()
    elif user_cfg["server"] == UserConfig._server.ThingsBoard:
        # Init server modules.
        server = TBDeviceMQTTClient(**server_cfg)
        tracker = TBTracker()
    else:
        raise ValueError("User config server is not compared.")
    tracker.add_module(settings)
    tracker.add_module(battery)
    tracker.add_module(history)
    tracker.add_module(net_manager)
    tracker.add_module(server)
    tracker.add_module(server_ota)
    tracker.add_module(gnss)
    tracker.add_module(cell)
    tracker.add_module(wifi)
    tracker.add_module(cyc)
    server.add_event("over_speed_alert")
    server.add_event("sim_abnormal_alert")
    server.add_event("low_power_alert")
    server.add_event("fault_alert")
    # Set net modules callback.
    net_manager.set_callback(tracker.net_callback)
    # Set server modules callback.
    server.set_callback(tracker.server_callback)
    # Start tracker business.
    tracker.running()

    log.debug("[x] Main over.")

if __name__ == "__main__":
    main()