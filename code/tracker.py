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
import net
import modem
import utime
import dataCall

from usr.modules.sensor import Sensor
from usr.modules.battery import Battery
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
        net.setModemFun(0)
        utime.sleep(3)
        net.setModemFun(1)
        utime.sleep(3)
        net_check_res = DeviceCheck().net()
        # if net_check_res[0] == 1 and net_check_res[1] != 1:
        #     log.warn("SIM abnormal!")
        #     alert_code = 30004
        #     alert_info = {"local_time": Collector().__get_local_time()}
        #     alert_data = Collector().__get_alert_data(alert_code, alert_info)
        #     Controller().device_data_report(event_data=alert_data, msg="sim_abnormal")
    else:
        if net_check_res == (3, 1):
            pass


def tracker():
    log.info("PROJECT_NAME: %s, PROJECT_VERSION: %s" % (PROJECT_NAME, PROJECT_VERSION))
    log.info("DEVICE_FIRMWARE_NAME: %s, DEVICE_FIRMWARE_VERSION: %s" % (DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION))

    current_settings = settings.get()

    # All device modules initialization
    # energy_led = LED()
    # running_led = LED()
    sensor = Sensor()
    history = History()
    battery = Battery()
    data_call = dataCall
    low_energy = LowEnergyManage()
    usb = USB() if USB is not None else None
    power_key = PowerKey() if PowerKey is not None else None
    locator = Location(current_settings["LocConfig"]["gps_mode"], current_settings["LocConfig"]["locator_init_params"])

    # DeviceCheck initialization
    devicecheck = DeviceCheck()
    # Add Location to DeviceCheck for checking whether locate is normal or not.
    devicecheck.add_module(locator)
    # Add Sensor to DeviceCheck for checking whether the sensor is normal or not.
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
        # Cloud object model init
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
        # Cloud object model init
        cloud_om = AliObjectModel()
        cloud.set_object_model(cloud_om)
    else:
        raise TypeError("Settings cloud[%s] is not support." % current_settings["sys"]["cloud"])

    # RemotePublish initialization
    remote_pub = RemotePublish()
    # Add History to RemotePublish for recording failure data
    remote_pub.addObserver(history)
    # Add Cloud to RemotePublish for publishing data to cloud
    remote_pub.add_cloud(cloud)

    # Controller initialization
    controller = Controller()
    # Add RemotePublish to Controller for publishing data to cloud
    controller.add_module(remote_pub)
    # Add Settings to Controller for changing settings.
    controller.add_module(settings)
    # Add LowEnergyManage to Controller for controlling low energy.
    controller.add_module(low_energy)
    # Add LED to Controller for show device status.
    # controller.add_module(energy_led, led_type="energy")
    # controller.add_module(running_led, led_type="running")
    # Add power_key to Controller for power key callback
    controller.add_module(power_key, callback=pwk_callback)
    # Add USB to Controller for get usb status
    controller.add_module(usb, callback=usb_callback)
    # Add dataCall to Controller for get net error callback
    controller.add_module(data_call)

    # Collector initialization
    collector = Collector()
    # Add Controller to Collector for puting command to control device.
    collector.add_module(controller)
    # Add DeviceCheck to Collector for getting device status.
    collector.add_module(devicecheck)
    # Add Battery to Collector for getting battery info.
    collector.add_module(battery)
    # Add Sensor to Collector for getting sensor info.
    collector.add_module(sensor)
    # Add Location to Collector for getting location info.
    collector.add_module(locator)
    # Add History to Collector for getting history data.
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
    # Report history
    collector.report_history()
    # OTA status init
    collector.ota_status_init()
    # Device modules status check
    collector.device_status_check()
    # Device info report to cloud
    controller.remote_device_report()
    if current_settings["user_cfg"]["sw_ota"] is True:
        # OTA plain check
        controller.remote_ota_check()
    # Low energy init
    controller.low_energy_init()
    # Low energy start
    controller.low_energy_start()
