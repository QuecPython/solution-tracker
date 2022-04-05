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
import app_fota
import uzlib
import ql_fs
import uhashlib
import ubinascii
import app_fota_download
from queue import Queue

from usr.logging import getLogger
from usr.settings import SYSNAME
from usr.settings import PROJECT_NAME

log = getLogger(__name__)


def OTA(object):

    def __init__(self, module, file_info):
        self.module = module
        self.file_info = file_info
        self.fota_queue = Queue(maxsize=4)

    def start(self):
        if self.module == SYSNAME:
            return self.start_fota()
        elif self.module == PROJECT_NAME:
            return self.start_sota()
        else:
            log.error('OTA Module %s Is Not Error!' % self.module)
            return False

    def start_fota(self):
        fota_obj = fota()
        url1 = self.file_info[0]['url']
        url2 = self.file_info[1]['url'] if len(self.file_info) > 1 else ''
        res = fota_obj.httpDownload(url1=url1, url2=url2, callback=self.fota_cb)
        if res == 0:
            fota_res = self.fota_queue.get()
            return fota_res
        else:
            return False

    def fota_cb(self, args):
        down_status = args[0]
        down_process = args[1]
        if down_status != -1:
            log.debug('DownStatus: %s [%s][%s%%]' % (down_status, '=' * down_process, down_process))
            if down_status == 0 and down_process == 100:
                self.fota_queue.put(True)
                # TODO: Report To Cloud Upgrade Process.
        else:
            log.error('Down Failed. Error Code: %s' % down_process)
            self.fota_queue.put(False)

    def start_sota(self):
        ota_module_obj = SotaDownloadUpgrade()
        for file in self.file_info:
            if ota_module_obj.app_fota_down(file['url']):
                if ota_module_obj.file_update(file['md5']):
                    continue
                else:
                    return False
            else:
                return False
        ota_module_obj.sota_set_flag()

        return True


class SotaDownloadUpgrade(object):
    def __init__(self, parent_dir="/usr/.updater/usr/"):
        self.fp_file = "/usr/sotaFile.tar.gz"
        self.file_list = []
        self.parent_dir = parent_dir
        self.unzipFp = 0
        self.hash_obj = uhashlib.md5()

    def write_update_data(self, data):
        with open(self.fp_file, "wb+") as fp:
            fp.write(data)
            self.hash_obj.update(data)

    def app_fota_down(self, url):
        app_fota_obj = app_fota.new()
        fp = open(self.fp_file, "wb+")
        fp.close()
        res = app_fota_obj.download(url, self.fp_file)
        if res == 0:
            self.hash_obj = uhashlib.md5()
            with open(self.fp_file, "rb+") as fp:
                for fpi in fp.readlines():
                    self.hash_obj.update(fpi)
            return True
        else:
            return False

    def __get_file_size(self, data):
        size = data.decode('ascii')
        size = size.rstrip('\0')
        if (len(size) == 0):
            return 0
        size = int(size, 8)
        return size

    def __get_file_name(self, name):
        fileName = name.decode('ascii')
        fileName = fileName.rstrip('\0')
        return fileName

    def file_update(self, md5_value):
        md5Data = ubinascii.hexlify(self.hash_obj.digest())
        md5Data = md5Data.decode('ascii')
        md5Value = eval(md5_value)
        log.debug("DMP Calc MD5 Value: %s, Device Calc MD5 Value: %s" % (md5Value, md5Data))
        if (md5Value != md5Data):
            log.error("MD5 Verification Failed")
            return

        log.debug("MD5 Verification Success.")
        ota_file = open(self.fp_file, "wb+")
        ota_file.seek(10)
        self.unzipFp = uzlib.DecompIO(ota_file, -15)
        log.debug('Unzip File Success.')
        ql_fs.mkdirs(self.parent_dir)
        try:
            while True:
                data = self.unzipFp.read(0x200)
                if not data:
                    log.debug("Read File Size Zore.")
                    break
                size = self.__get_file_size(data[124:135])
                fileName = self.__get_file_name(data[:100])
                log.debug("File Name: %s, File Size: %s" % (fileName, size))
                if not size:
                    if len(fileName):
                        log.debug("Create File Dir: %s" % self.parent_dir + fileName)
                        ql_fs.mkdirs(self.parent_dir + fileName)
                    else:
                        log.debug("Have No File Unzip.")
                        break
                else:
                    log.debug("File %s Write Size %s" % (self.parent_dir + fileName, size))
                    fp = open(self.parent_dir + fileName, "wb+")
                    fileSize = size
                    while fileSize:
                        data = self.unzipFp.read(0x200)
                        if (fileSize < 0x200):
                            fp.write(data[:fileSize])
                            fileSize = 0
                            fp.close()
                            self.file_list.append({"fileName": "/usr/" + fileName, "size": size})
                            break
                        else:
                            fileSize -= 0x200
                            fp.write(data)

            for fileName in self.file_list:
                app_fota_download.update_download_stat("/usr/.updater" + fileName["fileName"], fileName["fileName"], fileName["size"])
            ota_file.close()
            log.debug("Remove /usr/sotaFile.tar.gz")
            uos.remove("/usr/sotaFile.tar.gz")
        except Exception as e:
            log.error("Unpack Error: %s" % e)
            return False
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
