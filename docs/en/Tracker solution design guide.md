[中文](../zh/定位器方案设计指导.md) | **English** |

# Tracker Solution Design Guide

## Introduction

This document describes the design framework of Quecel smart tracker in the QuecPython solution, including the software and hardware system framework, description of key components, introduction and functional examples of system initialization process and business process, to help you quickly understand the overall architecture and functions of Quectel smart tracker.

## Function Overview

The software functions of smart tracker solution are demonstrated in the diagram below. The solution is divided into functions based on the actual business of the tracker and developed in a modular way.

![solution-tracker-101](./media/solution-tracker-101.png)

- Transmission Protocol Parsing
    + Connection and data interaction with Alibaba IoT Platform
    + Connection and data interaction with ThingsBoard
    + GT06 protocol
    + JT/T808 protocol
- Network Management
    + MQTT protocol (Alibaba IoT/ThingsBoard/other platforms)
    + TCP/UDP protocol (GT06/JTT808 protocol)
    + APN settings (network registration and data call)
    + LTE NET (4G network registration and data call)
- Peripheral Management
    + GNSS: Turn on/off the GNSS module, read positioning data from the GNSS module, and inject AGPS data.
    + G-sensor: Read data of sensors
    + Charge IC: Charging management, obtaining device charging status
    + Battery: Battery management, reading battery voltage and calculating battery level
    + LED: LED indicator
- Data Storage
    + Storage of system configuration parameters
    + Storage of location data backup
    + AGPS download storage
    + Log information storage
- Device Upgrade
    + OTA upgrade
- Business Function Management
    + Connection and reconnection of network and IoT platforms
    + Device data acquisition and reporting
    + Alarm detection and reporting
    + Processing of IoT platform downlink commands
    + Device low power consumption

## Data Interaction Process

The data interaction process between the module and the IoT platform is described in the following diagram.

![solution-tracker-102](./media/solution-tracker-102.png)

Process description:

1. The mobile APP sends commands to the IoT platform. The server issues commands to the module through TCP/UDP/MQTT protocols, and the module parses the command data.
2. The module reports data to the IoT platform through TCP/UDP/MQTT protocols. The IoT platform processes the data and synchronously displays it on the mobile APP.

## Software Framework

### Design Philosophy and Patterns

- This system is designed as a listener pattern, that is, transmit messages and listen for events through callback functions.
- The software functions are split according to the tracker's business requirements, which are implemented based on functional modules. Each part is independently developed to reduce dependencies and can be debugged and run independently, thus achieving decoupling effects.
- Interactions between functions are realized through callback functions. All business function processing, such as downlink command processing, alarm detection, data acquisition and reporting, and device control, is done in the `Tracker` class.

![solution-tracker-104](./media/solution-tracker-104.png)

1. All functional modules are registered in the `Tracker` class through `Tracker.add_module`.
2. The Server module (IoT platform interaction module) transmits service downlink data to `Tracker.server_callback()` for processing through callback functions.
3. The NetManage module transmits network disconnection events to `Tracker.net_callback` for processing through callback functions.

### Software Architecture Diagram

The software system framework is described as follows:

- Display layer, connection with different IoT platforms
- Transport layer, data interaction over different protocols
- Business layer, mainly used for device data acquisition, device control, downlink commands receiving and processing of IoT platforms, and data integration and reporting.
- Device layer, functions including obtaining and parsing location data, reading sensor data, battery management and historical data storage, and device information acquisition and device functions setting, such as device version, IMEI number, APN settings, network data call and device low power consumption.

![solution-tracker-107](./media/solution-tracker-107.png)

## Component Introduction

### Core Business Module (Tracker)

1. Function Description

Implement core business logic, interact with the server and parse the data, and control device modules. All functions are passed and processed in the sub-thread of the business event message queue as events.

2. Implementation Principle

- Register functional modules to obtain data from various functional modules, such as location information, battery information, and sensor information.

```python
class Tracker:
    ...

    def add_module(self, module):
        # Register various functional modules to the Tracker class for control in the Tracker class
        if isinstance(module, AliIot):
            self.__server = module
        elif isinstance(module, AliIotOTA):
            self.__server_ota = module
        elif isinstance(module, Battery):
            self.__battery = module
        elif isinstance(module, History):
            self.__history = module
        elif isinstance(module, GNSS):
            self.__gnss = module
        elif isinstance(module, CellLocator):
            self.__cell = module
        elif isinstance(module, WiFiLocator):
            self.__wifi = module
        elif isinstance(module, NMEAParse):
            self.__nmea_parse = module
        elif isinstance(module, CoordinateSystemConvert):
            self.__csc = module
        elif isinstance(module, NetManage):
            self.__net_manage = module
        elif isinstance(module, PowerManage):
            self.__pm = module
        elif isinstance(module, TempHumiditySensor):
            self.__temp_sensor = module
        elif isinstance(module, Settings):
            self.__settings = module
        else:
            return False
        return True

    def running(self, args=None):
        if self.__running_tag == 1:
            return
        self.__running_tag = 1
        # Disable device sleep
        self.__pm.autosleep(0)
        self.__pm.set_psm(mode=0)
        # Start the sub-thread of listening for business event message queues
        self.__business_start()
        # Send version OTA upgrade command to the event queue for execution
        self.__business_queue.put((0, "ota_refresh"))
        # Send location data reporting event (including network connection, device data acquisition and device data reporting)
        self.__business_queue.put((0, "loc_report"))
        # Send the event of querying OTA upgrade
        self.__business_queue.put((0, "check_ota"))
        # Send the device sleep event
        self.__business_queue.put((0, "into_sleep"))
        self.__running_tag = 0
```

- Listen for the commands issued by the server through callback functions and perform business processing.

```python
class Tracker:
    ...

    def server_callback(self, args):
        # Pass the server's downlink message to the business event message queue for processing
        self.__business_queue.put((1, args))
```

```python
class Tracker:
    ...

    def __business_running(self):
        while True:
            data = self.__business_queue.get()
            with self.__business_lock:
                self.__business_tag = 1
                ...
                # Process IoT platform downlink commands
                if data[0] == 1:
                    self.__server_option(*data[1])
                self.__business_tag = 0
```

```python
class Tracker:
    ...

    def __server_option(self, topic, data):
        if topic.endswith("/property/set"):
            # Process the downlink message of setting properties
            self.__server_property_set(data)
        elif topic.find("/rrpc/request/") != -1:
            # Process the downlink message of transparent transmission data
            msg_id = topic.split("/")[-1]
            self.__server_rrpc_response(msg_id, data)
        elif topic.find("/thing/service/") != -1:
            # Process the downlink message of service data
            service = topic.split("/")[-1]
            self.__server_service_response(service, data)
        elif topic.startswith("/ota/device/upgrade/") or topic.endswith("/ota/firmware/get_reply"):
            # Process the downlink message of OTA upgrades
            user_cfg = self.__settings.read("user")
            if self.__server_ota_flag == 0:
                if user_cfg["sw_ota"] == 1:
                    self.__server_ota_flag = 1
                    if user_cfg["sw_ota_auto_upgrade"] == 1 or user_cfg["user_ota_action"] == 1:
                        # Perform the OTA upgrade after the conditions for the OTA upgrade have been met
                        self.__server_ota_process(data)
                    else:
                        self.__server_ota_flag = 0
                        self.__server_ota.set_ota_data(data["data"])
                        ota_info = self.__server_ota.get_ota_info()
                        ota_info["ota_status"] = 1
                        self.__server_ota_state_save(**ota_info)
                else:
                    module = data.get("data", {}).get("module")
                    self.__server.ota_device_progress(-1, "Device is not alowed ota.", module)
```

- Wake up the device from sleep through the RTC callback function and report business data.

```python
class Tracker:
    ...

    def __into_sleep(self):
        while True:
            if self.__business_queue.size() == 0 and self.__business_tag == 0:
                break
            utime.sleep_ms(500)
        user_cfg = self.__settings.read("user")
        # Automatically adjust the sleep mode (auto-sleep or PSM) based on the sleep duration
        if user_cfg["work_cycle_period"] < user_cfg["work_mode_timeline"]:
            self.__pm.autosleep(1)
        else:
            self.__pm.set_psm(mode=1, tau=user_cfg["work_cycle_period"], act=5)
        # Enable RTC to wake up the device at a specified time
        self.__set_rtc(user_cfg["work_cycle_period"], self.running)

    def __set_rtc(self, period, callback):
        # Set the RTC to wake up the device
        self.__business_rtc.enable_alarm(0)
        if callback and callable(callback):
            self.__business_rtc.register_callback(callback)
        atime = utime.localtime(utime.mktime(utime.localtime()) + period)
        alarm_time = (atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0)
        _res = self.__business_rtc.set_alarm(alarm_time)
        log.debug("alarm_time: %s, set_alarm res %s." % (str(alarm_time), _res))
        return self.__business_rtc.enable_alarm(1) if _res == 0 else -1
```

3. Registration of functional modules and callback function configuration

```python
def main():
    # Initialize the network management module
    net_manage = NetManage(PROJECT_NAME, PROJECT_VERSION)
    # Initialize the configuration parameter module
    settings = Settings()
    # Initialize the battery detection module
    battery = Battery()
    # Initialize the historical data module
    history = History()
    # Initialize the IoT platform (AliIot) module
    server_cfg = settings.read("server")
    server = AliIot(**server_cfg)
    # Initialize the IoT platform (AliIot) OTA module
    server_ota = AliIotOTA(PROJECT_NAME, FIRMWARE_NAME)
    server_ota.set_server(server)
    # Initialize the low power consumption module
    power_manage = PowerManage()
    # Initialize the temperature and humidity sensor module
    temp_sensor = TempHumiditySensor(i2cn=I2C.I2C1, mode=I2C.FAST_MODE)
    loc_cfg = settings.read("loc")
    # Initialize the GNSS positioning module
    gnss = GNSS(**loc_cfg["gps_cfg"])
    # Initialize the LBS positioning module
    cell = CellLocator(**loc_cfg["cell_cfg"])
    # Initialize the Wi-Fi positioning module
    wifi = WiFiLocator(**loc_cfg["wifi_cfg"])
    # Initialize the GNSS positioning data parsing module
    nmea_parse = NMEAParse()
    # Initialize the WGS84 to GCJ02 coordinate system conversion module
    cyc = CoordinateSystemConvert()

    # Initialize the Tracker business module
    tracker = Tracker()
    # Register the basic objects to the Tracker class for control
    tracker.add_module(settings)
    tracker.add_module(battery)
    tracker.add_module(history)
    tracker.add_module(net_manage)
    tracker.add_module(server)
    tracker.add_module(server_ota)
    tracker.add_module(power_manage)
    tracker.add_module(temp_sensor)
    tracker.add_module(gnss)
    tracker.add_module(cell)
    tracker.add_module(wifi)
    tracker.add_module(nmea_parse)
    tracker.add_module(cyc)

    # Set the callback function for the network module, which processes business when the network is disconnected
    net_manage.set_callback(tracker.net_callback)
    # Set the callback function for receiving downlink data from the server, which processes business when the server issues commands
    server.set_callback(tracker.server_callback)

    # Start the Tracker project business functions
    tracker.running()


if __name__ == "__main__":
    # Run the main file
    main()
```

### location

1. Function Description

Obtain the current device location information through built-in or external GNSS, LBS, and Wi-Fi.

2. Implementation Principle

- Turn on the GNSS module to read the location data from the built-in GNSS through *quecgnss.read()*.

```python
class GNSS:
    ...

    def __internal_read(self):
        log.debug("__internal_read start.")
        # Turn on GNSS
        self.__internal_open()

        # Clear the historical GNSS data cached in the serial port
        while self.__break == 0:
            gnss_data = quecgnss.read(1024)
            if gnss_data[0] == 0:
                self.__break = 1
        self.__break = 0

        self.__gps_nmea_data_clean()
        self.__gps_data_check_timer.start(2000, 1, self.__gps_data_check_callback)
        cycle = 0
        # Read raw GNSS data
        while self.__break == 0:
            gnss_data = quecgnss.read(1024)
            if gnss_data and gnss_data[1]:
                this_gps_data = gnss_data[1].decode() if len(gnss_data) > 1 and gnss_data[1] else ""
                self.__reverse_gps_data(this_gps_data)
                if self.__check_gps_valid():
                    self.__break = 1
            cycle += 1
            if cycle >= self.__retry:
                if self.__break != 1:
                    self.__break = 1
            if self.__break != 1:
                utime.sleep(1)
        self.__gps_data_check_timer.stop()
        self.__break = 0

self.__gps_data_check_callback(None)
        # Turn off GNSS
        self.__internal_close()
        log.debug("__internal_read %s." % ("success" if self.__get_gps_data() else "failed"))
        return self.__get_gps_data()
```

- Read the location data from the external GNSS module through the UART.

```python
class GNSS:
    ...

    def __external_read(self):
        # Open the UART for the external GNSS module
        self.__external_open()
        log.debug("__external_read start")

        # Clear the historical GNSS data cached in the UART
        while self.__break == 0:
            self.__gps_timer.start(50, 0, self.__gps_timer_callback)
            signal = self.__external_retrieve_queue.get()
            log.debug("[first] signal: %s" % signal)
            if signal:
                to_read = self.__external_obj.any()
                log.debug("[first] to_read: %s" % to_read)
                if to_read > 0:
                    self.__set_gps_data(self.__external_obj.read(to_read).decode())
            self.__gps_timer.stop()
        self.__break = 0

        self.__gps_nmea_data_clean()
        self.__gps_data_check_timer.start(2000, 1, self.__gps_data_check_callback)
        cycle = 0
        # Read raw GNSS data
        while self.__break == 0:
            self.__gps_timer.start(1500, 0, self.__gps_timer_callback)
            signal = self.__external_retrieve_queue.get()
            log.debug("[second] signal: %s" % signal)
            if signal:
                to_read = self.__external_obj.any()
                log.debug("[second] to_read: %s" % to_read)
                if to_read > 0:
                    self.__reverse_gps_data(self.__external_obj.read(to_read).decode())
                    if self.__check_gps_valid():
                        self.__break = 1

            self.__gps_timer.stop()
            cycle += 1
            if cycle >= self.__retry:
                self.__break = 1
            if self.__break != 1:
                utime.sleep(1)
        self.__gps_data_check_timer.stop()
        self.__break = 0

        # Check if GPS data is usable or not
        self.__gps_data_check_callback(None)
        # Close the UART for the external GNSS module
        self.__external_close()
        log.debug("__external_read %s." % ("success" if self.__get_gps_data() else "failed"))
        return self.__get_gps_data()
```

- Read the location data, including the latitude, longitude and accuracy, from the LBS through *cellLocator.getLocation()*.

```python
class CellLocator:
    ...

    def __read_thread(self):
        loc_data = ()
        try:
            # Read LBS-positioning data
            loc_data = cellLocator.getLocation(
                self.__serverAddr,
                self.__port,
                self.__token,
                self.__timeout,
                self.__profileIdx
            )
            loc_data = loc_data if isinstance(loc_data, tuple) and loc_data[0] and loc_data[1] else ()
        except Exception as e:
            sys.print_exception(e)
        self.__queue.put(loc_data)
```

- Read the location data, including the latitude, longitude, accuracy and MAC address, from the Wi-Fi through *wifilocator(token).getwifilocator()*.

```python
class WiFiLocator:

    def __init__(self, token):
        self.__wifilocator = wifilocator(token) if wifilocator else None

    def read(self):
        loc_data = -1
        try:
            return self.__wifilocator.getwifilocator() if self.__wifilocator else -1
        except Exception as e:
            sys.print_exception(e)
        return loc_data
```

### battery

1. Function Description

Read the battery level and voltage. Get the charging status of the battery and notify you of the status changes through callback functions.

2. Implementation Principles

- There are two ways to read the battery voltage
    + Get voltage through *Power.getVbatt()*
    + Calculate the voltage obtained through ADC

```python
class Battery(object):
    ...

    def __get_power_vbatt(self):
        """Get vbatt from power"""
        # Get voltage through Power.getVbatt()
        return int(sum([Power.getVbatt() for i in range(100)]) / 100)

    def __get_adc_vbatt(self):
        """Get vbatt from adc"""
        # Calculate the voltage obtained through ADC
        self.__adc.open()
        utime.sleep_ms(self.__adc_period)
        adc_list = list()
        for i in range(self.__adc_period):
            adc_list.append(self.__adc.read(self.__adc_num))
            utime.sleep_ms(self.__adc_period)
        adc_list.remove(min(adc_list))
        adc_list.remove(max(adc_list))
        adc_value = int(sum(adc_list) / len(adc_list))
        self.__adc.close()
        vbatt_value = adc_value * (self.__factor + 1)
        return vbatt_value
```

- The calculation of battery level is only an analog currently. You can get the fuzzy value based on the following table of data relationships between voltage, temperature, and battery level.

```python
BATTERY_OCV_TABLE = {
    "nix_coy_mnzo2": {
        55: {
            4152: 100, 4083: 95, 4023: 90, 3967: 85, 3915: 80, 3864: 75, 3816: 70, 3773: 65, 3737: 60, 3685: 55,
            3656: 50, 3638: 45, 3625: 40, 3612: 35, 3596: 30, 3564: 25, 3534: 20, 3492: 15, 3457: 10, 3410: 5, 3380: 0,
        },
        20: {
            4143: 100, 4079: 95, 4023: 90, 3972: 85, 3923: 80, 3876: 75, 3831: 70, 3790: 65, 3754: 60, 3720: 55,
            3680: 50, 3652: 45, 3634: 40, 3621: 35, 3608: 30, 3595: 25, 3579: 20, 3548: 15, 3511: 10, 3468: 5, 3430: 0,
        },
        0: {
            4147: 100, 4089: 95, 4038: 90, 3990: 85, 3944: 80, 3899: 75, 3853: 70, 3811: 65, 3774: 60, 3741: 55,
            3708: 50, 3675: 45, 3651: 40, 3633: 35, 3620: 30, 3608: 25, 3597: 20, 3585: 15, 3571: 10, 3550: 5, 3500: 0,
        },
    },
}
```

```python
class Battery:
    ...

    def __get_soc_from_dict(self, key, volt_arg):
        """Get battery energy from map"""
        if BATTERY_OCV_TABLE[self.__battery_ocv].get(key):
            volts = sorted(BATTERY_OCV_TABLE[self.__battery_ocv][key].keys(), reverse=True)
            pre_volt = 0
            volt_not_under = 0  # Determine whether the voltage is lower than the minimum voltage value of soc.
            for volt in volts:
                if volt_arg > volt:
                    volt_not_under = 1
                    soc1 = BATTERY_OCV_TABLE[self.__battery_ocv][key].get(volt, 0)
                    soc2 = BATTERY_OCV_TABLE[self.__battery_ocv][key].get(pre_volt, 0)
                    break
                else:
                    pre_volt = volt
            if pre_volt == 0:  # Input Voltarg > Highest Voltarg
                return soc1
            elif volt_not_under == 0:
                return 0
            else:
                return soc2 - (soc2 - soc1) * (pre_volt - volt_arg) // (pre_volt - volt)

    def __get_soc(self, temp, volt_arg):
        """Get battery energy by temperature and voltage"""
        if temp > 30:
            return self.__get_soc_from_dict(55, volt_arg)
        elif temp < 10:
            return self.__get_soc_from_dict(0, volt_arg)
        else:
            return self.__get_soc_from_dict(20, volt_arg)
```

- The battery\'s state of charge is determined by interrupting the pin and obtaining the high and low levels of the pin.

```python
class Battery:
    ...

    def __update_charge_status(self):
        """Update Charge status by gpio status"""
        if not self.__usb:
            chrg_level = self.__chrg_gpio.read()
            stdby_level = self.__stdby_gpio.read()
            if chrg_level == 1 and stdby_level == 1:
                # Not charge.
                self.__charge_status = 0
            elif chrg_level == 0 and stdby_level == 1:
                # Charging.
                self.__charge_status = 1
            elif chrg_level == 1 and stdby_level == 0:
                # Charge over.
                self.__charge_status = 2
            else:
                raise TypeError("CHRG and STDBY cannot be 0 at the same time!")
        else:
            self.__usb_charge()

    @property
    def charge_status(self):
        """Get charge status
        Returns:
            0 - Not charged
            1 - Charging
            2 - Finished charging
        """
        self.__update_charge_status()
        return self.__charge_status

```

### power_manage

1. Function Description

Wake up the device periodically and process business logic. After the business processing is completed, the device enters sleep mode.

Two sleep modes are supported currently.

- auto-sleepauto-sleep
- PSM

2. Implementation Principle

Set the corresponding sleep mode to make the device enter sleep mode, and wake up the device by RTC.

```python
class PowerManage:
    ...

    def autosleep(self, val):
        """Set device autosleep.

        Args:
            val (int): 0 - disable, 1 - enable.

        Returns:
            bool: True - success. False - failed.
        """
        return True if hasattr(pm, "autosleep") and val in (0, 1) and pm.autosleep(val) == 0 else False

    def set_psm(self, mode=1, tau=None, act=None):
        """Set device psm.

        Args:
            mode (int): 0 - disable psm, 1 - enable psm.
            tau (int/None): tau seconds. When mode is 0, this value is None. (default: `None`)
            act (int/None): act seconds. When mode is 0, this value is None. (default: `None`)

        Returns:
            bool: True - success. False - failed.
        """
        if not hasattr(pm, "set_psm_time") or not hasattr(pm, "get_psm_time"):
            return False
        if mode == 0:
            return pm.set_psm_time(0)
        else:
            self.__init_tau(tau)
            self.__init_act(act)
            res = pm.set_psm_time(self.__tau_unit, self.__tau_time, self.__act_unit, self.__act_time)
            log.info("set_psm_time: %s" % res)
            if res:
                get_psm_res = pm.get_psm_time()
                log.debug("get_psm_res: %s" % str(get_psm_res))
                if get_psm_res[0] == 1 and get_psm_res[1:] == [self.__tau_unit, self.__tau_time, self.__act_unit, self.__act_time]:
                    log.debug("PSM time equal set time.")
            return res
```

### aliyunIot

1. Function Description

Interact with Alibaba IoT Platform over the MQTT protocol.

- Connect and log in to the platform
- Send TSL model data to the server
- Receive commands from the server
- Perform OTA upgrade

> Alibaba IoT Platform over MQTT protocol is taken as an example here. The actual application should be developed according to the actual IoT platform and protocol and the basic logic is similar.

2. Implementation Principle

Log in to Alibaba IoT Platform and interact with it according to the communication rules over the MQTT protocol.

- Register an account and log in

```python
class AliIot:
    ...

    def connect(self):
        res = -1
        self.__server = "%s.%s" % (self.__product_key, self.__domain)
        log.debug("self.__product_key: %s" % self.__product_key)
        log.debug("self.__product_secret: %s" % self.__product_secret)
        log.debug("self.__device_name: %s" % self.__device_name)
        log.debug("self.__device_secret: %s" % self.__device_secret)
        log.debug("self.__server: %s" % self.__server)
        self.__server = aLiYun(self.__product_key, self.__product_secret, self.__device_name, self.__device_secret, self.__server)
        res = self.__server.setMqtt(self.__device_name)
        if res == 0:
            self.__server.setCallback(self.__subscribe_callback)
            res = self.__subscribe_topics()
            if res == 0:
                self.__server.start()
        return res
```

- Report data

```python
class AliIot:
    ...

    def properties_report(self, data):.
        # Report properties
        _timestamp = self.__timestamp
        _id = self.__id
        params = {key: {"value": val, "time": _timestamp} for key, val in data.items()}
        properties = {
            "id": _id,
            "version": "1.0",
            "sys": {
                "ack": 1
            },
            "params": params,
            "method": "thing.event.property.post",
        }
        pub_res = self.__server.publish(self.ica_topic_property_post, ujson.dumps(properties), qos=self.__qos) if self.__server else -1
        return self.__get_post_res(_id) if pub_res is True else False

    def event_report(self, event, data):
        # Report events
        _timestamp = self.__timestamp
        _id = self.__id
        params = {"value": data, "time": _timestamp}
        properties = {
            "id": _id,
            "version": "1.0",
            "sys": {
                "ack": 1
            },
            "params": params,
            "method": "thing.event.%s.post" % event,
        }
        pub_res = self.__server.publish(self.ica_topic_event_post.format(event), ujson.dumps(properties), qos=self.__qos) if self.__server else -1
        return self.__get_post_res(_id) if pub_res is True else False
```

- Respond to the downlink data

```python
class AliIot:
    ...

    def __subscribe_callback(self, topic, data):
        topic = topic.decode()
        try:
            data = ujson.loads(data)
        except:
            pass
        log.debug("topic: %s, data: %s" % (topic, str(data)))

        if topic.endswith("/post_reply"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 200 else False)
            return
        elif topic.endswith("/thing/ota/firmware/get_reply"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 200 else False)

        if self.__callback and callable(self.__callback):
            # Pass the data to Tracker.server_callback() for processing
            self.__callback((topic, data))
```

- OTA Upgrade

```python
class AliIotOTA:
    ...

    def start(self):
        # Start an OTA upgrade
        if self.__module == self.__project_name:
            self.__start_sota()
        elif self.__module == self.__firmware_name:
            self.__start_fota()
        else:
            return False
        return True

    def __start_fota(self):
        log.debug("__start_fota")
        fota_obj = fota()
        url1 = self.__files[0]["url"]
        url2 = self.__files[1]["url"] if len(self.__files) > 1 else ""
        log.debug("start httpDownload")
        if url2:
            res = fota_obj.httpDownload(url1=url1, url2=url2, callback=self.__fota_callback) if fota_obj else -1
        else:
            res = fota_obj.httpDownload(url1=url1, callback=self.__fota_callback) if fota_obj else -1
        log.debug("httpDownload res: %s" % res)
        if res == 0:
            self.__ota_timer.start(600 * 1000, 0, self.__ota_timer_callback)
            fota_res = self.__fota_queue.get()
            self.__ota_timer.stop()
            return fota_res
        else:
            self.__server.ota_device_progress(-2, "Download File Failed.", module=self.__module)
            return False
```

### UML Class Diagram

The following is a UML class figure depicting the dependencies and inheritance relationships of all component objects in the project software codes. "Tracker" is the top-level object and is associated with the dependent component objects.

![solution-tracker-104](./media/solution-tracker-104.png)

## Event Flow Description

### Business Process

![solution-tracker-105](media/solution-tracker-105.png)

Business Process Description:

1. Power on the device.
2. Configure APN and connect to the network (network registration and data call); Configure IoT platform and establish a connection, with retry on failure.
3. Detect the boot of objects and acquire data.
    - Power on the GNSS object and wait for positioning data.
    - Power on the G-Sensor and detect the calibration.
    - Turn on LED indicators (network status/positioning status/charging status, etc.).
    - Acquire battery level and detect charging status.
    - Detect alarms (overspeed/vibration/geo-fence/low battery level, etc.).
4. After connecting to the IoT platform, check if there is any historical data that needs to be reported and proceed with reporting.
5. Upon successful connection to the IoT platform, report current device information (location/alarms).
6. If the connection to the IoT platform fails, store the current device information (location/alarms).
7. When the device has no tasks, enter low power mode and wake up the device periodically to detect device information and report it.
8. After connecting to the IoT platform, wait for commands to be issued by the IoT platform
9. Parse commands
    - Device control commands, such as modifying device business parameters and controlling device shutdown or reboot.
    - OTA upgrade commands for OTA upgrades
    - Device information query commands, which should be responded with device information

### System Initialization Process

![solution-tracker-106](media/solution-tracker-106.png)

1. Initialize basic functional objects, such as low power management, configuration parameters, battery, historical files, positioning, and sensors.
2. Initialize IoT platform server object, such as Alibaba IoT Platform, ThingsBoard, or other private service platform (GT06, JT/T808, etc.).
3. Initialize the core business object (Tracker), and add various functional objects to the Tracker object through *tracker.add_module()*, then register *Tracker.server_callback()* to the Server object for receiving downlink messages and commands from the server.
