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

from usr.logging import getLogger
from usr.common import Observable, CloudObserver

log = getLogger(__name__)


class RemoteSubcribe(CloudObserver):
    def __init__(self):
        self.__executor = None

    def get_executor(self):
        return self.__executor

    def set_executor(self, executor):
        if executor:
            self.__executor = executor
            return True
        return False

    def raw_data(self, *args, **kwargs):
        return self.__executor.event_option(*args, **kwargs) if self.__executor else False

    def object_model(self, *args, **kwargs):
        return self.__executor.event_done(*args, **kwargs) if self.__executor else False

    def query(self, *args, **kwargs):
        return self.__executor.event_query(*args, **kwargs) if self.__executor else False

    def ota_plain(self, *args, **kwargs):
        return self.__executor.event_ota_plain(*args, **kwargs) if self.__executor else False

    def ota_file_download(self, *args, **kwargs):
        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        log.debug("ota_file_download: %s" % str(args))
        if self.__executor and hasattr(self.__executor, "ota_file_download"):
            return self.__executor.event_ota_file_download(*args, **kwargs)
        else:
            return False

    def execute(self, observable, *args, **kwargs):
        """
        1. observable: Cloud Iot Object.
        2. args[1]: Cloud DownLink Data Type.
        2.1 object_model: Set Cloud Object Model.
        2.2 query: Query Cloud Object Model.
        2.3 ota_plain: OTA Plain Info.
        2.4 raw_data: Passthrough Data (Not Support Now).
        2.5 ota_file_download: Download OTA File For MQTT Association (Not Support Now).
        3. args[2]: Cloud DownLink Data(List Or Dict).
        """
        opt_attr = args[1]
        opt_args = args[2] if not isinstance(args[2], dict) else ()
        opt_kwargs = args[2] if isinstance(args[2], dict) else {}
        if hasattr(self, opt_attr):
            option_fun = getattr(self, opt_attr)
            return option_fun(*opt_args, **opt_kwargs)
        else:
            log.error("RemoteSubcribe Has No Attribute [%s]." % opt_attr)
            return False


class RemotePublish(Observable):

    def __init__(self):
        """
        cloud:
            CloudIot Object
        """
        super().__init__()
        self.__cloud = None

    def __cloud_conn(self, enforce=False):
        return self.__cloud.init(enforce=enforce) if self.__cloud else False

    def __cloud_post(self, data):
        return self.__cloud.post_data(data) if self.__cloud else False

    def set_cloud(self, cloud):
        if hasattr(cloud, "init") and \
                hasattr(cloud, "post_data") and \
                hasattr(cloud, "ota_request") and \
                hasattr(cloud, "ota_action"):
            self.__cloud = cloud
            return True
        return False

    def cloud_ota_check(self):
        return self.__cloud.ota_request() if self.__cloud else False

    def cloud_ota_action(self, action=1, module=None):
        return self.__cloud.ota_action(action, module) if self.__cloud else False

    def post_data(self, data):
        """
        Data format to post:

        {
            "switch": True,
            "energy": 100,
            "non_gps": [],
            "gps": []
        }
        """
        res = True
        if self.__cloud_conn():
            if not self.__cloud_post(data):
                if self.__cloud_conn(enforce=True):
                    if not self.__cloud_post(data):
                        res = False
                else:
                    log.error("Cloud Connect Failed.")
                    res = False
        else:
            log.error("Cloud Connect Failed.")
            res = False

        if res is False:
            # This Observer Is History
            self.notifyObservers(self, *[data])

        return res

    # TODO: Remove To Business Module
    def post_history(self, hist):
        res = True

        if hist["data"]:
            pt_count = 0
            for i, data in enumerate(hist["data"]):
                pt_count += 1
                if not self.post_data(data):
                    res = False
                    break

            hist["data"] = hist["data"][pt_count:]
            if hist["data"]:
                # Flush data in hist-dictionary to tracker_data.hist file.
                self.notifyObservers(self, *hist["data"])

        return res
