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

import modem
import utime
import osTimer

from usr.logging import Logger
from usr.tracker import tracker
from usr.battery import Battery
from usr.history import History
from usr.location import Location, _loc_method, GPSMatch, GPSParse
from usr.quecthing import QuecThing, QuecObjectModel
from usr.aliyunIot import AliYunIot, AliObjectModel
from usr.mpower import LowEnergyManage
from usr.common import Observable, Observer
from usr.remote import RemoteSubscribe, RemotePublish
from usr.settings import Settings, PROJECT_NAME, PROJECT_VERSION, \
    DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION, LocConfig, \
    AliCloudConfig, QuecCloudConfig

log = Logger(__name__)


def test_led():
    pass


def test_logger():
    res = {"all": 0, "success": 0, "failed": 0}

    log = Logger("test_logger")
    log.debug("debug Level Log.")
    log.info("info Level Log.")
    log.warn("warn Level Log.")
    log.error("error Level Log.")
    log.critical("critical Level Log.")

    assert log.get_debug() is True, "[test_logger] FAILED: log.get_debug() is not True."
    print("[test_logger] SUCCESS: log.get_debug() is True.")
    res["success"] += 1

    assert log.set_debug(True) is True, "[test_logger] FAILED: log.set_debug(True)."
    print("[test_logger] SUCCESS: log.set_debug(True).")
    res["success"] += 1
    assert log.set_debug(False) is True, "[test_logger] FAILED: log.set_debug(False)."
    print("[test_logger] SUCCESS: log.set_debug(False).")
    res["success"] += 1

    assert log.get_level() == "debug", "[test_logger] FAILED: log.get_level() is not debug."
    print("[test_logger] SUCCESS: log.get_level() is debug.")
    res["success"] += 1

    for level in ("debug", "info", "warn", "error", "critical"):
        assert log.set_level(level) is True and log.get_level() == level, "[test_logger] FAILED: log.set_level(%s)." % level
        print("[test_logger] SUCCESS: log.set_level(%s)." % level)
        res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_logger] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


def test_settings():
    res = {"all": 0, "success": 0, "failed": 0}
    settings = Settings()

    assert settings.init() is True, "[test_settings] FAILED: Settings.init()."
    print("[test_settings] SUCCESS: Settings.init().")
    res["success"] += 1

    current_settings = settings.get()
    assert current_settings and isinstance(current_settings, dict)
    print("[test_settings] SUCCESS: Settings.get().")
    res["success"] += 1

    for key, val in current_settings.get("user_cfg", {}).items():
        val = "18888888888" if key == "phone_num" else val
        if key == "work_mode_timeline":
            set_res = False
        else:
            set_res = True
        assert settings.set(key, val) is set_res, "[test_settings] FAILED: APP Settings.set(%s, %s)." % (key, val)
        print("[test_settings] SUCCESS: APP Settings.set(%s, %s)." % (key, val))
        res["success"] += 1

    cloud_params = current_settings["cloud"]
    assert settings.set("cloud", cloud_params) is True, "[test_settings] FAILED: SYS Settings.set(%s, %s)." % ("cloud", str(cloud_params))
    print("[test_settings] SUCCESS: SYS Settings.set(%s, %s)." % ("cloud", str(cloud_params)))
    res["success"] += 1

    assert settings.save() is True, "[test_settings] FAILED: Settings.save()."
    print("[test_settings] SUCCESS: Settings.save().")
    res["success"] += 1

    assert settings.reset() is True, "[test_settings] FAILED: Settings.reset()."
    print("[test_settings] SUCCESS: Settings.reset().")
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_settings] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


run_time = 0


def get_voltage_cb(args):
    global run_time
    run_time += 5


def test_battery():
    res = {"all": 0, "success": 0, "failed": 0}
    battery = Battery()

    temp = 30
    msg = "[test_battery] %s: battery.set_temp(30)."
    assert battery.set_temp(temp) and battery.__temp == temp, msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    timer = osTimer()
    timer.start(5, 1, get_voltage_cb)
    voltage = battery.get_voltage()
    timer.stop()
    global run_time
    print("[test_battery] battery.get_voltage() run_time: %sms" % run_time)
    msg = "[test_battery] %s: battery.get_voltage() %s."
    assert isinstance(voltage, int) and voltage > 0, msg % ("FAILED", voltage)
    print(msg % ("SUCCESS", voltage))
    res["success"] += 1

    energy = battery.get_energy()
    assert isinstance(energy, int) and energy >= 0, "[test_battery] FAILED: battery.get_energy() %s." % energy
    print("[test_battery] SUCCESS: battery.get_energy() is %s." % energy)
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_battery] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


class TestHistObservable(Observable):

    def produce_hist_data(self, local_time):
        hist_data = [{"local_time": local_time}]
        self.notifyObservers(self, *hist_data)


def test_history():
    res = {"all": 0, "success": 0, "failed": 0}

    history = History()
    test_hist_obs = TestHistObservable()
    test_hist_obs.addObserver(history)

    hist_data = [{"test": "test"}]
    assert history.write(hist_data), "[test_history] FAILED: history.write()."
    print("[test_history] SUCCESS: history.write(%s)." % str(hist_data))
    res["success"] += 1

    hist = history.read()
    assert hist.get("data") is not None and isinstance(hist["data"], list), "[test_history] FAILED: history.read() %s." % hist
    print("[test_history] SUCCESS: history.read() is %s." % hist)
    res["success"] += 1

    local_time = utime.mktime(utime.localtime())
    test_hist_obs.produce_hist_data(local_time)
    hist = history.read()
    obs_res = False
    for i in hist.get("data", []):
        if i.get("local_time") == local_time:
            obs_res = True
            break
    assert obs_res, "[test_history] FAILED: history.update() %s." % str(hist)
    print("[test_history] SUCCESS: history.update() %s." % str(hist))
    res["success"] += 1

    assert history.clean(), "[test_history] FAILED: history.clean()."
    print("[test_history] SUCCESS: history.clean().")
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_history] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


def test_location():
    res = {"all": 0, "success": 0, "failed": 0}

    settings = Settings()
    current_settings = settings.get()
    gps_mode = 0x2
    locator_init_params = current_settings["LocConfig"]["locator_init_params"]

    locator = Location(gps_mode, locator_init_params)
    for loc_method in range(1, 8):
        loc_data = locator.read(loc_method)
        if loc_method & 0x1:
            assert loc_data.get(0x1) not in ("", (), None), "[test_location] FAILED: locator.read(%s) loc_data: %s." % (loc_method, loc_data)
        if loc_method & 0x2:
            assert loc_data.get(0x2) not in ("", (), None), "[test_location] FAILED: locator.read(%s) loc_data: %s." % (loc_method, loc_data)
        if loc_method & 0x4:
            assert loc_data.get(0x4) not in ("", (), None), "[test_location] FAILED: locator.read(%s) loc_data: %s." % (loc_method, loc_data)
        print("[test_location] SUCCESS: locator.read(%s) loc_data: %s." % (loc_method, loc_data))
        res["success"] += 1

    res["all"] = res["success"] + res["failed"]

    print("[test_location] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


def get_quec_loc_data(loc_method, loc_data):
    __gps_match = GPSMatch()

    if loc_method == 0x1:
        res = {"gps": []}
        r = __gps_match.GxRMC(loc_data)
        if r:
            res["gps"].append(r)

        r = __gps_match.GxGGA(loc_data)
        if r:
            res["gps"].append(r)

        r = __gps_match.GxVTG(loc_data)
        if r:
            res["gps"].append(r)
        return res
    elif loc_method == 0x2:
        return {"non_gps": ["LBS"]}
    elif loc_method == 0x4:
        return {"non_gps": []}


def test_quecthing():
    res = {"all": 0, "success": 0, "failed": 0}

    settings = Settings()
    current_settings = settings.get()

    cloud_init_params = QuecCloudConfig.__dict__
    cloud = QuecThing(
        cloud_init_params["PK"],
        cloud_init_params["PS"],
        cloud_init_params["DK"],
        cloud_init_params["DS"],
        cloud_init_params["SERVER"],
        mcu_name=PROJECT_NAME,
        mcu_version=PROJECT_VERSION
    )
    remote_sub = RemoteSubscribe()
    cloud.addObserver(remote_sub)

    quec_om = QuecObjectModel()
    msg = "[test_quecthing] %s: cloud.set_object_model(%s)."
    assert cloud.set_object_model(quec_om), msg % ("FAILED", quec_om)
    print(msg % ("SUCCESS", quec_om))
    res["success"] += 1

    msg = "[test_quecthing] %s: cloud.init()."
    assert cloud.init(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_quecthing] %s: get_quec_loc_data(%s, %s) %s."
    loc_method = _loc_method.gps
    gps_mode = LocConfig._gps_mode.external
    locator_init_params = current_settings["LocConfig"]["locator_init_params"]

    locator = Location(gps_mode, locator_init_params)
    loc_data = locator.read(loc_method)
    quec_loc_data = get_quec_loc_data(loc_method, loc_data.get(loc_method))
    assert quec_loc_data != "", msg % ("FAILED", loc_method, loc_data, quec_loc_data)
    print(msg % ("SUCCESS", loc_method, loc_data, quec_loc_data))
    res["success"] += 1

    msg = "[test_quecthing] %s: cloud.post_data(%s)."
    assert cloud.post_data(quec_loc_data), msg % ("FAILED", str(quec_loc_data))
    print(msg % ("SUCCESS", str(quec_loc_data)))
    res["success"] += 1

    msg = "[test_quecthing] %s: cloud.ota_request()."
    assert cloud.ota_request(), msg % ("FAILED",)
    print(msg % ("SUCCESS",))
    res["success"] += 1

    # # PASS: No OTA Plain, ota_action Return False
    # msg = "[test_quecthing] %s: cloud.ota_action()."
    # assert cloud.ota_action() is True, msg % ("FAILED",)
    # print(msg % ("SUCCESS",))

    msg = "[test_quecthing] %s: cloud.close()."
    assert cloud.close(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_quecthing] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


def get_ali_loc_data(loc_method, loc_data):
    res = {"GeoLocation": {}}

    __gps_match = GPSMatch()
    __gps_parse = GPSParse()

    if loc_method == 0x1:
        gga_data = __gps_match.GxGGA(loc_data)
        data = {}
        if gga_data:
            Latitude = __gps_parse.GxGGA_latitude(gga_data)
            if Latitude:
                data["Latitude"] = float("%.2f" % float(Latitude))
            Longtitude = __gps_parse.GxGGA_longtitude(gga_data)
            if Longtitude:
                data["Longtitude"] = float("%.2f" % float(Longtitude))
            Altitude = __gps_parse.GxGGA_altitude(gga_data)
            if Altitude:
                data["Altitude"] = float("%.2f" % float(Altitude))
            if data:
                data["CoordinateSystem"] = 1
        res = {"GeoLocation": data}
    elif loc_method in (0x2, 0x4):
        if loc_data:
            res["GeoLocation"] = {
                "Longtitude": round(loc_data[0], 2),
                "Latitude": round(loc_data[1], 2),
                # "Altitude": 0.0,
                "CoordinateSystem": 1
            }

    return res


def test_aliyuniot():
    res = {"all": 0, "success": 0, "failed": 0}

    settings = Settings()
    current_settings = settings.get()

    cloud_init_params = AliCloudConfig.__dict__
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
    remote_sub = RemoteSubscribe()
    cloud.addObserver(remote_sub)

    ali_om = AliObjectModel()
    msg = "[test_aliyuniot] %s: cloud.set_object_model(%s)."
    assert cloud.set_object_model(ali_om), msg % ("FAILED", ali_om)
    print(msg % ("SUCCESS", ali_om))
    res["success"] += 1

    msg = "[test_aliyuniot] %s: cloud.init()."
    assert cloud.init(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_aliyuniot] %s: get_ali_loc_data(%s, %s) %s."
    loc_method = _loc_method.gps
    gps_mode = LocConfig._gps_mode.external
    locator_init_params = current_settings["LocConfig"]["locator_init_params"]

    locator = Location(gps_mode, locator_init_params)
    loc_data = locator.read(loc_method)
    ali_loc_data = get_ali_loc_data(loc_method, loc_data.get(loc_method))
    assert ali_loc_data["GeoLocation"] != {}, msg % ("FAILED", loc_method, loc_data, ali_loc_data)
    print(msg % ("SUCCESS", loc_method, loc_data, ali_loc_data))
    res["success"] += 1

    msg = "[test_aliyuniot] %s: cloud.post_data(%s)."
    assert cloud.post_data(ali_loc_data), msg % ("FAILED", str(ali_loc_data))
    print(msg % ("SUCCESS", str(ali_loc_data)))
    res["success"] += 1

    msg = "[test_aliyuniot] %s: cloud.ota_request()."
    assert cloud.ota_request(), msg % ("FAILED",)
    print(msg % ("SUCCESS",))
    res["success"] += 1

    msg = "[test_aliyuniot] %s: cloud.device_report()."
    assert cloud.device_report(), msg % ("FAILED",)
    print(msg % ("SUCCESS",))
    res["success"] += 1

    # # PASS: No OTA Plain, ota_action Return False
    # msg = "[test_aliyuniot] %s: cloud.ota_action()."
    # assert cloud.ota_action() is True, msg % ("FAILED",)
    # print(msg % ("SUCCESS",))

    msg = "[test_aliyuniot] %s: cloud.close()."
    assert cloud.close() and cloud.__ali.getAliyunSta() != 0, msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_aliyuniot] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


def test_remote():
    res = {"all": 0, "success": 0, "failed": 0}

    settings = Settings()
    current_settings = settings.get()
    cloud_init_params = current_settings["cloud"]

    cloud = QuecThing(
        cloud_init_params["PK"],
        cloud_init_params["PS"],
        cloud_init_params["DK"],
        cloud_init_params["DS"],
        cloud_init_params["SERVER"],
        mcu_name=PROJECT_NAME,
        mcu_version=PROJECT_VERSION
    )
    remote_sub = RemoteSubscribe()
    cloud.addObserver(remote_sub)
    remote_pub = RemotePublish()

    msg = "[test_remote] %s: cloud.cloud_init()."
    assert cloud.cloud_init(), msg % "FAILED"
    print(msg % "SUCCESS")

    msg = "[test_remote] %s: remote_pub.set_cloud(cloud)."
    assert remote_pub.set_cloud(cloud), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_remote] %s: remote_pub.get_cloud()."
    assert isinstance(remote_pub.get_cloud(), QuecThing), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_remote] %s: remote_pub.cloud_ota_check()."
    assert remote_pub.cloud_ota_check(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    # # PASS: No OTA Plain, ota_action Return False
    # msg = "[test_remote] %s: remote_pub.ota_request()."
    # assert remote_pub.ota_request(), msg % "FAILED"
    # print(msg % "SUCCESS")

    gps_mode = 0x2
    locator_init_params = current_settings["user_cfg"]["locator_init_params"]
    locator = Location(gps_mode, locator_init_params)

    loc_method = 0x1
    loc_data = locator.read(loc_method)
    quec_loc_data = cloud.get_loc_data(loc_method, loc_data.get(loc_method))

    msg = "[test_remote] %s: remote_pub.post_data(%s)."
    assert remote_pub.post_data(quec_loc_data), msg % ("FAILED", str(quec_loc_data))
    print(msg % ("SUCCESS", str(quec_loc_data)))
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_remote] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


class TestLEMObserver(Observer):

    def update(self, observable, *args, **kwargs):
        log.debug("observable: %s" % observable)
        log.debug("args: %s" % str(args))
        log.debug("kwargs: %s" % str(kwargs))
        observable.start()
        return True


def test_low_energy_manage():
    res = {"all": 0, "success": 0, "failed": 0}

    low_energy_manage = LowEnergyManage()
    test_lem_obs = TestLEMObserver()
    low_energy_manage.addObserver(test_lem_obs)

    period = 5
    msg = "[test_low_energy_manage] %s: low_energy_manage.set_period(%s)."
    assert low_energy_manage.set_period(period), msg % ("FAILED", period)
    print(msg % ("SUCCESS", period))
    res["success"] += 1

    msg = "[test_low_energy_manage] %s: low_energy_manage.get_period()."
    assert low_energy_manage.get_period() == period, msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    low_energy_method = "PM"
    msg = "[test_low_energy_manage] %s: low_energy_manage.set_low_energy_method(%s)."
    assert low_energy_manage.set_low_energy_method(low_energy_method), msg % ("FAILED", low_energy_method)
    print(msg % ("SUCCESS", low_energy_method))
    res["success"] += 1

    msg = "[test_low_energy_manage] %s: low_energy_manage.get_low_energy_method()."
    assert low_energy_manage.get_low_energy_method() == low_energy_method, msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_low_energy_manage] %s: low_energy_manage.low_energy_init()."
    assert low_energy_manage.low_energy_init(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_low_energy_manage] %s: low_energy_manage.get_lpm_fd()."
    assert low_energy_manage.get_lpm_fd() is not None, msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    msg = "[test_low_energy_manage] %s: low_energy_manage.start()."
    assert low_energy_manage.start(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    utime.sleep(period * 3 + 1)
    msg = "[test_low_energy_manage] %s: low_energy_manage.stop()."
    assert low_energy_manage.stop(), msg % "FAILED"
    print(msg % "SUCCESS")
    res["success"] += 1

    res["all"] = res["success"] + res["failed"]
    print("[test_low_energy_manage] ALL: %s SUCCESS: %s, FAILED: %s." % (res["all"], res["success"], res["failed"]))


def test_tracker():
    tracker()


def main():
    # test_logger()
    # test_settings()
    # test_battery()
    # test_history()
    # test_location()
    # test_quecthing()
    # test_aliyuniot()
    # test_remote()
    # test_low_energy_manage()
    test_tracker()


if __name__ == "__main__":
    main()
