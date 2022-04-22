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

from usr.tracker import tracker
from usr.settings import Settings
from usr.modules.logging import getLogger

log = getLogger(__name__)


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


def test_tracker():
    tracker()


def main(test_fun="test_tracker"):
    test_funs = ["test_settings", "test_tracker"]
    if test_fun not in test_funs and callable(locals().get(test_fun)):
        print("test_fun[%s] is not exists." % test_fun)
        return

    locals()[test_fun]()


if __name__ == "__main__":
    main()
