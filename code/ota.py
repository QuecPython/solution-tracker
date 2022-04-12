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

import uos
import fota
import uzlib
import ql_fs
import app_fota
import uhashlib
import ubinascii
import app_fota_download

from queue import Queue

from usr.logging import getLogger

log = getLogger(__name__)

FOTA_ERROR_CODE = {
    1001: "FOTA_DOMAIN_NOT_EXIST",
    1002: "FOTA_DOMAIN_TIMEOUT",
    1003: "FOTA_DOMAIN_UNKNOWN",
    1004: "FOTA_SERVER_CONN_FAIL",
    1005: "FOTA_AUTH_FAILED",
    1006: "FOTA_FILE_NOT_EXIST",
    1007: "FOTA_FILE_SIZE_INVALID",
    1008: "FOTA_FILE_GET_ERR",
    1009: "FOTA_FILE_CHECK_ERR",
    1010: "FOTA_INTERNAL_ERR",
    1011: "FOTA_NOT_INPROGRESS",
    1012: "FOTA_NO_MEMORY",
    1013: "FOTA_FILE_SIZE_TOO_LARGE",
    1014: "FOTA_PARAM_SIZE_INVALID",
}


class OTA(object):

    def __init__(self, file_info, ota_type="FOTA", ota_cb=None):
        self.file_info = file_info
        self.ota_type = ota_type
        self.ota_cb = ota_cb
        self.fota_queue = Queue(maxsize=4)

    def start(self):
        if self.ota_type == "FOTA":
            return self.start_fota()
        elif self.ota_type == "SOTA":
            return self.start_sota()
        else:
            log.error("OTA Type %s Is FOTA Or SOTA Error!" % self.ota_type)
            return False

    def fota_cb(self, args):
        down_status = args[0]
        down_process = args[1]
        if down_status in (0, 1):
            # TODO: Report To Cloud Upgrade Process.
            log.debug("DownStatus: %s [%s][%s%%]" % (down_status, "=" * down_process, down_process))
        elif down_status == 2:
            # Download Over & Check Over, To Power Restart Update.
            self.fota_queue.put(True)
        else:
            log.error("Down Failed. Error Code [%s] %s" % (down_process, FOTA_ERROR_CODE.get(down_process, down_process)))
            self.fota_queue.put(False)
        if self.ota_cb:
            self.ota_cb(args)

    def start_fota(self):
        fota_obj = fota()
        url1 = self.file_info[0]["url"]
        url2 = self.file_info[1]["url"] if len(self.file_info) > 1 else ""
        res = fota_obj.httpDownload(url1=url1, url2=url2, callback=self.fota_cb)
        if res == 0:
            fota_res = self.fota_queue.get()
            return fota_res
        else:
            return False

    def start_sota(self):
        ota_module_obj = SOTA()
        for file in self.file_info:
            if ota_module_obj.app_fota_down(file["url"]):
                if ota_module_obj.check_md5(file["md5"]):
                    if ota_module_obj.file_update():
                        continue
                    else:
                        return False
                else:
                    return False
            else:
                return False
        ota_module_obj.sota_set_flag()

        return True


class SOTA(object):
    def __init__(self, parent_dir="/usr/.updater/usr/"):
        self.fp_file = "/usr/sotaFile.tar.gz"
        self.parent_dir = parent_dir
        self.hash_obj = None

    def write_update_data(self, data):
        with open(self.fp_file, "wb+") as fp:
            fp.write(data)
            self.hash_obj.update(data)

    def app_fota_down(self, url):
        app_fota_obj = app_fota.new()
        res = app_fota_obj.download(url, self.fp_file)
        if res == 0:
            uos.rename("/usr/.updater" + self.fp_file, self.fp_file)
            self.hash_obj = uhashlib.md5()
            with open(self.fp_file, "rb+") as fp:
                for fpi in fp.readlines():
                    self.hash_obj.update(fpi)
            return True
        else:
            return False

    def __get_file_size(self, data):
        size = data.decode("ascii")
        size = size.rstrip("\0")
        if (len(size) == 0):
            return 0
        size = int(size, 8)
        return size

    def __get_file_name(self, name):
        fileName = name.decode("ascii")
        fileName = fileName.rstrip("\0")
        return fileName

    def check_md5(self, cloud_md5):
        file_md5 = ubinascii.hexlify(self.hash_obj.digest())
        file_md5 = file_md5.decode("ascii")
        log.debug("DMP Calc MD5 Value: %s, Device Calc MD5 Value: %s" % (cloud_md5, file_md5))
        if (cloud_md5 != file_md5):
            log.error("MD5 Verification Failed")
            return False

        log.debug("MD5 Verification Success.")
        return True

    def file_update(self):
        ota_file = open(self.fp_file, "rb+")
        ota_file.seek(10)
        unzipFp = uzlib.DecompIO(ota_file, -15)
        log.debug("Unzip File Success.")
        ql_fs.mkdirs(self.parent_dir)
        file_list = []
        try:
            while True:
                data = unzipFp.read(0x200)
                if not data:
                    log.debug("Read File Size Zore.")
                    break

                size = self.__get_file_size(data[124:135])
                fileName = self.__get_file_name(data[:100])
                log.debug("File Name: %s, File Size: %s" % (fileName, size))

                if not size:
                    if len(fileName):
                        log.debug("Create File: %s" % self.parent_dir + fileName)
                        ql_fs.mkdirs(self.parent_dir + fileName)
                    else:
                        log.debug("Have No File Unzip.")
                        break
                else:
                    log.debug("File %s Write Size %s" % (self.parent_dir + fileName, size))
                    fp = open(self.parent_dir + fileName, "wb+")
                    fileSize = size
                    while fileSize:
                        data = unzipFp.read(0x200)
                        if (fileSize < 0x200):
                            fp.write(data[:fileSize])
                            fileSize = 0
                            fp.close()
                            file_list.append({"fileName": "/usr/" + fileName, "size": size})
                            break
                        else:
                            fileSize -= 0x200
                            fp.write(data)

            for fileName in file_list:
                app_fota_download.update_download_stat("/usr/.updater" + fileName["fileName"], fileName["fileName"], fileName["size"])

            log.debug("Remove %s" % self.fp_file)
            uos.remove(self.fp_file)
        except Exception as e:
            log.error("Unpack Error: %s" % e)
            return False
        finally:
            ota_file.close()

        return True

    def sota_set_flag(self):
        app_fota_download.set_update_flag()


class OTAFileClear(object):
    def __init__(self):
        self.usrList = uos.ilistdir("/usr/")

    def __remove_updater_dir(self, path):
        dirList = uos.ilistdir(path)
        for fileInfo in dirList:
            if fileInfo[1] == 0x4000:
                self.__remove_updater_dir("%s/%s" % (path, fileInfo[0]))
            else:
                log.debug("remove file name: %s/%s" % (path, fileInfo[0]))
                uos.remove("%s/%s" % (path, fileInfo[0]))

        log.debug("remove dir name: %s" % path)
        uos.remove(path)

    def file_clear(self):
        for fileInfo in self.usrList:
            if fileInfo[0] == ".updater":
                self.__remove_updater_dir("/usr/.updater")
            elif fileInfo[0] == "sotaFile.tar.gz":
                log.debug("remove update file sotaFile.tar.gz")
                uos.remove("/usr/sotaFile.tar.gz")
