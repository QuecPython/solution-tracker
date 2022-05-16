# Tracker 公版方案用户指导手册

## 项目简介

> 项目旨在为Python开发者提供一个Tracker项目的功能模板与组件，方便开发者快速开发Tracker嵌入式业务功能。

## 内置功能模块

- [x] 阿里云(aliyunIot): 提供阿里云物联网物模型的消息发布与订阅，OTA升级功能。
- [x] 移远云(quecthing): 提供移远云物联网物模型的消息发布与订阅，OTA升级功能。
- [x] 电池模块(battery): 提供设电池电量，电压数据查询，充电状态查询功能。
- [x] LED模块(led): 提供LED开关控制功能，周期性闪烁功能。
- [x] 定位模块(location): 提供内置/外置GPS，基站，WIFI定位查询功能。
- [x] 日志模块(logging): 提供日志打印功能。
- [x] 低功耗模块(mpower): 提供周期性低功耗唤醒功能。
- [x] 云服务中间件(remote): 提供云服务消息处理中间件功能。
- [ ] 传感器功能(sensor): 开发中...

## 项目结构

```
|--code
    |--aliyun_object_model.json
    |--main.py
    |--quec_object_model.json
    |--settings.py
    |--settings_alicloud.py
    |--settings_jtt808.py
    |--settings_loc.py
    |--settings_queccloud.py
    |--settings_sys.py
    |--settings_user.py
    |--test_tracker.py
    |--tracker.py
    |--tracker_collector.py
    |--tracker_controller.py
    |--tracker_devicecheck.py
    |--modules
        |--aliyunIot.py
        |--battery.py
        |--common.py
        |--history.py
        |--led.py
        |--location.py
        |--logging.py
        |--mpower.py
        |--quecthing.py
        |--remote.py
        |--sensor.py
```

### 功能模块注册流程图

![](./media/tracker_modules_registration_process.png)

## 项目拉取

```bash
# 下载主项目代码
git clone https://gitee.com/qpy-solutions/tracker-v2.git

# 进入主项目目录
cd tracker-v2/

# 切换对应的主项目分支
git checkout master

# 子项目初始化
git submodule init

# 子项目代码拉取
git submodule update

# 进入子项目目录
cd code/modules/

# 切换对应的子项目分支
git checkout master
```

## 项目配置

### 硬件设备

推荐的硬件设备

- 内置GNSS设备: EC200UCNAA
- 外置GNSS设备: EC600NCNLA/EC600NCNLC

### 云服务平台

- 目前项目支持移远云，阿里云
- 创建物联网平台产品和设备(移远云无需创建设备)
    + [阿里云物联网平台相关文档](https://help.aliyun.com/product/30520.html)
    + [移远云物联网平台相关文档](https://iot-cloud-docs.quectelcn.com/homepage/)
- 项目提供了[阿里云tracker物模型demo](https://gitee.com/qpy-solutions/tracker-v2/blob/dev/object_model_demo/ali_cloud_object_model.json)和[移远云tracker物模型demo](https://gitee.com/qpy-solutions/tracker-v2/blob/dev/object_model_demo/quec_cloud_object_model.json)，可以直接导入使用，用户亦可根据自己的实际需求进行物模型的定义
- 将云平台物模型导出(阿里云可导出精简模式)json格式，放入代码根目录`code`下
    + 阿里云物模型json文件建议命名: `aliyun_object_model.json`
    + 移远云物模型json文件建议命名: `quec_object_model.json`

### 设置项目配置参数

- 设置云服务平台链接配置参数
    + 移远云连接配置: `settings_queccloud.py`
    + 阿里云连接配置: `settings_alicloud.py`
- 设置定位模块相关配置参数 `settings_loc.py`

```python
# settings_queccloud.py
PK = "{ProductKey}"
PS = "{ProductSecret}"
DK = ""
DS = ""

# settings_alicloud.py

PK = "{ProductKey}"
PS = "{ProductSecret}"
DK = "{DeviceName}"
DS = "{DeviceSecret}"

SERVER = "%s.iot-as-mqtt.cn-shanghai.aliyuncs.com" % PK
client_id = ""
life_time = 120
burning_method = _burning_method.one_machine_one_secret  # 一机一密或一型一密

# settings_loc.py

_gps_cfg = {
    "UARTn": UART.UART1,
    "buadrate": 115200,
    "databits": 8,
    "parity": 0,
    "stopbits": 1,
    "flowctl": 0,
    "PowerPin": None,
    "StandbyPin": None,
    "BackupPin": None
}

_cell_cfg = {
    "serverAddr": "www.queclocator.com",
    "port": 80,
    "token": "XXXX",  # 密钥，16位字符组成，需要申请
    "timeout": 3,
    "profileIdx": profile_idx,
}

_wifi_cfg = {
    "token": "XXXX"  # 密钥，16位字符组成，需要申请
}
```

## 启动项目

直接使用项目提供的物模型，当各个模块配置都已就绪后，将项目代码按项目结构(`code`即`usr`目录)导入设备`/usr/`目录下，设备会自动运行`main.py`，通过QPYcom交互界面即可看到消息上传日志，同时查看云服务平台设备信息，即可看到上传的数据信息。

## 二次开发

当使用自定义物模型时，需重写`tracker_collector.py`, `settings_user.py`两个文件

### 数据采集器修改(`tracker_collector.py` )

- 用户可继承或修改`Collector`类进二次开发
- 以下基础功能方法，不可删除，用户可根据实际业务需求修改函数内处理逻辑
    + `add_module`: 添加功能模块
    + `event_option`: 云服务透传数据处理
    + `event_done`: 云服务物模型设置数据处理
    + `event_query`: 云服务物模型查询数据处理
    + `event_ota_plain`: 云服务OTA升级计划处理
    + `event_ota_file_download`: 云服务OTA文件分片下载处理
    + `low_engery_option`: 低功耗周期唤醒业务处理
    + `update`: 接收被监听者消息通知功能
- 用户可新增其他方法用于业务处理

### 业务配置文件(`settings_user.py`)

该模块为业务配置文件，用户可根据实际情况进行使用调整。

### DEMO样例

周期性上传定位信息到云端

```python
from usr.settings import PROJECT_NAME, PROJECT_VERSION, \
    DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION, settings, SYSConfig
from usr.tracker_collector import Collector
from usr.tracker_controller import Controller

from usr.modules.history import History
from usr.modules.location import Location
from usr.modules.mpower import LowEnergyManage
from usr.modules.remote import RemotePublish, RemoteSubscribe
from usr.modules.aliyunIot import AliYunIot, AliObjectModel
from usr.modules.quecthing import QuecThing, QuecObjectModel


def TestCollector(Collector):

    def loc_report(self):
        # Get cloud location data
        loc_info = self.__read_location()
        cloud_loc = self.__read_cloud_location(loc_info)
        return self.__controller.remote_post_data(device_data)

    def low_engery_option(self, low_energy_method):
        """Business option after low energy waking up."""
        if not self.__controller:
            raise TypeError("self.__controller is not registered.")

        self.loc_report()

        if low_energy_method == "POWERDOWN":
            self.__controller.power_down()


current_settings = settings.get()

# 初始化历史文件存储模块
history = History()
# 初始化低功耗模块
low_energy = LowEnergyManage()
# 初始化定位模块
locator = Location(current_settings["LocConfig"]["gps_mode"], current_settings["LocConfig"]["locator_init_params"])

cloud_init_params = current_settings["cloud"]
if current_settings["sys"]["cloud"] & SYSConfig._cloud.quecIot:
    # 初始化移远云服务模块
    cloud = QuecThing(
        cloud_init_params["PK"],
        cloud_init_params["PS"],
        cloud_init_params["DK"],
        cloud_init_params["DS"],
        cloud_init_params["SERVER"],
        mcu_name=PROJECT_NAME,
        mcu_version=PROJECT_VERSION
    )
    # 转化物模型json为对象
    cloud_om = QuecObjectModel()
    # 将物模型实例对象注册到云服务对象中
    cloud.set_object_model(cloud_om)
elif current_settings["sys"]["cloud"] & SYSConfig._cloud.AliYun:
    client_id = cloud_init_params["client_id"] if cloud_init_params.get("client_id") else modem.getDevImei()
    # 初始化阿里云服务模块
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
    # 转化物模型json为对象
    cloud_om = AliObjectModel()
    # 将物模型实例对象注册到云服务对象中
    cloud.set_object_model(cloud_om)
else:
    raise TypeError("Settings cloud[%s] is not support." % current_settings["sys"]["cloud"])

# 初始化云服务发布消息中间件
remote_pub = RemotePublish()
# 添加历史文件模块到云服务发布消息中间件中，当发送失败时将数据存入历史文件中
remote_pub.addObserver(history)
# 添加云服务模块到云服务发布消息中间件中，用于消息的发布
remote_pub.add_cloud(cloud)

# 初始化控制模块
controller = Controller()
# 添加云服务发布消息中间件到控制模块
controller.add_module(remote_pub)
# 添加低功耗模块到控制模块中
controller.add_module(low_energy)

# 初始化数据采集模块
collector = TestCollector()
# 添加控制模块到数据采集模块，用于控制设备模块与发送数据
collector.add_module(controller)
# 添加定位模块到数据采集模块，用于查询定位信息.
collector.add_module(locator)

# 初始化低功耗模块
work_cycle_period = current_settings["user_cfg"]["work_cycle_period"]
# 设置低功耗唤醒周期
low_energy.set_period(work_cycle_period)
# 根据低功耗唤醒周期和设备选择低功耗模式
low_energy.set_low_energy_method(collector.__init_low_energy_method(work_cycle_period))
# 添加数据采集者作为低功耗模块的监听者，接收唤醒消息
low_energy.addObserver(collector)

# 初始化云服务消息订阅中间件
remote_sub = RemoteSubscribe()
# 添加数据采集这作为云服务消息订阅中间件的监听者，接收云端下发的消息指令
remote_sub.add_executor(collector)
# 云服务模块添加云服务消息订阅中间件作为云服务模块的监听者，接收云端下发的消息指令
cloud.addObserver(remote_sub)

# 云服务初始化连接
cloud.init()
# 上报定位信息
collector.loc_report()

# 低功耗休眠初始化
controller.low_energy_init()
# 启动低功耗休眠
controller.low_energy_start()

```
