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

import sim
import modem
import dataCall

from usr.modules.sensor import Sensor
from usr.modules.battery import Battery
from usr.modules.ota import OTAFileClear
from usr.modules.history import History
from usr.modules.logging import getLogger
from usr.modules.mpower import LowEnergyManage
from usr.modules.remote import RemotePublish, RemoteSubscribe
from usr.modules.aliyunIot import AliYunIot, AliObjectModel
from usr.modules.quecthing import QuecThing, QuecObjectModel
from usr.modules.location import Location
from usr.settings import PROJECT_NAME, PROJECT_VERSION, \
    DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION, settings, SYSConfig
from usr.tracker_collector import Collector
from usr.tracker_controller import Controller
from usr.tracker_devicecheck import DeviceCheck

try:
    from misc import USB
except ImportError:
    USB = None
try:
    from misc import PowerKey
except ImportError:
    PowerKey = None


log = getLogger(__name__)

sim.setSimDet(1, 0)


def pwk_callback(status):
    if status == 0:
        log.info("PowerKey Release.")
    elif status == 1:
        log.info("PowerKey Press.")
    else:
        log.warn("Unknown PowerKey Status:", status)


def usb_callback(status):
    if status == 0:
        log.info("USB is disconnected.")
    elif status == 1:
        log.info("USB is connected.")
    else:
        log.warn("Unknown USB Stauts:", status)


def nw_callback(args):
    net_check_res = DeviceCheck().net()
    if args[1] != 1:
        if net_check_res[0] == 1 and net_check_res[1] != 1:
            log.warn("SIM abnormal!")
            alert_code = 30004
            alert_info = {"local_time": Collector().__get_local_time()}
            alert_data = Collector().__get_alert_data(alert_code, alert_info)
            Controller().device_data_report(event_data=alert_data, msg="sim_abnormal")
    else:
        if net_check_res == (3, 1):
            pass


def tracker():
    current_settings = settings.get()

    # All device modules initialization
    # energy_led = LED()
    # running_led = LED()
    sensor = Sensor()
    history = History()
    battery = Battery()
    data_call = dataCall
    low_energy = LowEnergyManage()
    ota_file_clear = OTAFileClear()
    usb = USB() if USB is not None else None
    power_key = PowerKey() if PowerKey is not None else None
    locator = Location(current_settings["LocConfig"]["gps_mode"], current_settings["LocConfig"]["locator_init_params"])

    # DeviceCheck initialization
    devicecheck = DeviceCheck()
    devicecheck.add_module(locator)
    devicecheck.add_module(sensor)

    # Cloud initialization
    cloud_init_params = current_settings["cloud"]
    if current_settings["sys"]["cloud"] & SYSConfig._cloud.quecIot:
        cloud = QuecThing(
            cloud_init_params["PK"],
            cloud_init_params["PS"],
            cloud_init_params["DK"],
            cloud_init_params["DS"],
            cloud_init_params["SERVER"],
            mcu_name=PROJECT_NAME,
            mcu_version=PROJECT_VERSION
        )
        cloud_om = QuecObjectModel()
        cloud.set_object_model(cloud_om)
    elif current_settings["sys"]["cloud"] & SYSConfig._cloud.AliYun:
        client_id = cloud_init_params["client_id"] if cloud_init_params.get("client_id") else modem.getDevImei()
        cloud = AliYunIot(
            cloud_init_params["PK"],
            cloud_init_params["PS"],
            cloud_init_params["DK"],
            cloud_init_params["DS"],
            cloud_init_params["SERVER"],
            client_id,
            burning_method=cloud_init_params["burning_method"],
            mcu_name=PROJECT_NAME,
            mcu_version=PROJECT_VERSION,
            firmware_name=DEVICE_FIRMWARE_NAME,
            firmware_version=DEVICE_FIRMWARE_VERSION
        )
        cloud_om = AliObjectModel()
        cloud.set_object_model(cloud_om)
    else:
        raise TypeError("Settings cloud[%s] is not support." % current_settings["sys"]["cloud"])

    # RemotePublish initialization
    remote_pub = RemotePublish()
    remote_pub.addObserver(history)
    remote_pub.add_cloud(cloud)

    # Controller initialization
    controller = Controller()
    controller.add_module(remote_pub)
    controller.add_module(settings)
    controller.add_module(low_energy)
    controller.add_module(ota_file_clear)
    # controller.add_module(energy_led, led_type="energy")
    # controller.add_module(running_led, led_type="running")
    controller.add_module(power_key, callback=pwk_callback)
    controller.add_module(usb, callback=usb_callback)
    controller.add_module(data_call)

    # Collector initialization
    collector = Collector()
    collector.add_module(controller)
    collector.add_module(devicecheck)
    collector.add_module(battery)
    collector.add_module(sensor)
    collector.add_module(locator)
    collector.add_module(history)

    # LowEnergyManage initialization
    work_cycle_period = current_settings["user_cfg"]["work_cycle_period"]
    low_energy.set_period(work_cycle_period)
    low_energy.set_low_energy_method(collector.__init_low_energy_method(work_cycle_period))
    low_energy.addObserver(collector)

    # RemoteSubscribe initialization
    remote_sub = RemoteSubscribe()
    remote_sub.add_executor(collector)
    cloud.addObserver(remote_sub)

    # Business start
    # Cloud start
    cloud.init()
    # OTA upgrade file clean
    controller.ota_file_clean()
    # Device modules status check
    collector.device_status_check()
    # Low energy init
    controller.low_energy_init()
    # Low energy start
    controller.low_energy_start()
