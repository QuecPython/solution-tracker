# Tracker 公版方案功能接口

## Tracker 功能列表

### 设备自动开关机与指示灯

#### 低电关机

- 开机状态下，电量≤`低电关机阈值(默认5%)`时，自动关机，关闭一切指示灯，并在关机前，需向云端报告一次设备信息。

#### 开机自检及运行状态指示灯(网络、GPS检测开发完成, 其他开发中)

- 开机自检
    - 检测网络、GPS模组、各类传感器(照度传感器，温湿度传感器，三轴加速度传感器)、麦克风是否正常工作；
- 运行状态指指示灯(根据开机自检结果显示)：
    - 正常：运行状态指示灯2s闪烁一次。
    - 异常：运行状态指示灯500ms闪烁一次；在网络正常的情况下，需向云端发出故障报警。

#### 电量指示灯(开发中)

- `低电告警阈值(默认30%)`<电量：常亮
- `低电关机阈值(默认5%)`<电量<=`低电告警阈值(默认30%)`：1秒闪烁一次
- 电量<=`低电关机阈值(默认5%)`：熄灭

### 设备信息交互功能

#### 多重定位

- 由GPS、WiFi或基站综合确定位置信息。
- 默认GPS定位，具体使用哪一种或几种定位技术，可由云端或手机APP控制。

#### 电子围栏(开发中)

- 由云端规划设备安全区域。 当设备位置超出安全区域，云端向设置的联系方式发送报警信息，如设置邮箱发送报警邮件，设置手机号拨打报警电话或发送报警短信。
- 该功能由云端支持。

#### 语音监听(开发中)

- 云端登记的手机号拨打tracker中的手机号时，自动接听，监听现场的声音。
- 功能的开启，可由云端或手机APP控制。默认开启该功能。

#### 录音上报(开发中)

- 自动录音并上报的功能，可由云端或手机APP控制。默认关闭该功能。

#### 部标808协议(开发中)

- 与云端之间的通信遵循808协议。

#### 设备信息上报

- 上报设备定位信息，电量，开关机状态，定位方式，电话号码等信息；
- 默认上报设备信息的场景：
    1. 周期性定时
    2. 报警发生时
    3. 语音监听时
    4. 录音时
- 根据不同的应用场景，上报工作模式分别有以下三种：
    1. 周期性模式 -- 周期性上报设备信息，上报完成后进入低功耗模式
    2. 智能模式 -- 开启GPS定位时，运动上报，上报完成后进入低功耗模式，静止不上报直接进入低功耗模式
- 上报工作模式与上报周期，由云端或手机APP控制，默认周期性上报，上报周期30秒。

#### OTA升级(开发中)

- 上电时，待网络连接后，检测是否需要更新升级。
- 如有升级：
    - 若非自动升级，则上云端上报有新的更新；
    - 在云端或手机APP点击升级按钮；
    - 下载升级包，并将升级包准备完毕的通知报给云端(移远云无需上报下载后直接升级)；
    - 升级完毕后，将升级状态报告给云端。
- 功能的开启，可由云端或手机APP控制。默认开启该功能。
- 功能开启的状态下，可由云端或手机APP配置是否自动升级。默认开启自动升级。

#### 远程配置或控制
- 远程配置：电话号码、远程配置定位器工作模式、定位使用的技术手段、语音监听、自动录音上报、固件升级及自动升级、故障报警、低电报警、超速报警、SIM卡异常报警、拆卸报警、振动报警和驾驶行为监测功能的开关。
- 远程控制：远程控制固件升级的流程。

### 设备报警功能

#### 故障报警

- 设备在开机自检或正常工作中遇到了故障时报警。
- 功能的开启，可由云端或手机APP控制。默认开启该功能。
- 报警代码：20000

#### 低电报警

- 电量低于设定值时报警。
- 低电的阈值默认为5%，可由云端或手机APP设置，但设定值限制在5%-30%。
- 功能的开启，可由云端或手机APP控制。默认开启该功能。
- 报警代码：30002

#### 超速报警

- 速度超过设定值时报警。
- 功能的开启，超速阈值，可由云端或手机APP控制。默认关闭该功能。
- 报警代码：30003

#### SIM卡异常报警

- SIM卡拔出时报警，此时网络不通，按照网络不通的逻辑处理。
- 功能的开启，可由云端或手机APP控制。默认开启该功能。
- 报警代码：30004

#### 拆卸报警(开发中)

- 照度传感器检测到较亮的光线时报警。
- 功能的开启，可由云端或手机APP控制。默认开启该功能。
- 报警代码：30005

#### 驾驶行为监测(开发中)

- 检测到急起急停或急转弯时，报驾驶行为异常。
- 功能的开启，可由云端或手机APP控制。默认关闭该功能。
- 驾驶行为异常的报警代码为：
    - 急起：40001
    - 急停：40002
    - 左急转弯：40003
    - 右急转弯：40004

#### SOS一键报警(开发中)

- 长按功能键5s，紧急求助。
- 先向云端发送紧急报警信息，同时向内置电话号码拨打电话、发送短信。
- 报警代码：50001

## Tracker 功能模块说明

### 功能模块注册流程图

![](./media/tracker_modules_registration_process.png)

### 功能模块说明

#### 业务功能模块

| 模块名称 | 模块功能 |
|---|---|
| settings | 配置参数读写模块。 |
| settings_cloud | 云服务端连接参数配置模块。 |
| settings_loc | 定位模块参数配置。 |
| settings_user | 用户业务功能配置参数模块。 |
| tracker_ali | 阿里云 Tracker 业务功能。 |
| tracker_tb | ThingsBoard Tracker 业务功能。 |

#### 设备功能模块

| 模块名称 | 模块功能 |
|---|---|
| aliyunIot | 阿里云模块，主要用于与云端的消息交互与OTA升级 |
| battery | 电池模块，获取电池电量与电压 |
| buzzer | 蜂鸣器模块，获取控制蜂鸣器开关 |
| common | 公共方法模块 |
| history | 历史文件读写操作模块 |
| led | 控制LED亮灭闪烁功能模块 |
| location | 定位模块，可获取GPS，基站，WIFI三种定位方式的定位信息 |
| logging | 提供日志信息展示与存储功能 |
| net_manage | 设备网络功能管理模块 |
| temp_humidity_sensor | 温湿度传感器模块, 读取当前设备温湿度参数 |
| thingsboard | ThingsBoard 平台MQTT客户端功能, 用于与云端的消息交互 |

## Tracker API v2.1.0

### settings

#### 全局变量

- `PROJECT_NAME` -- 项目名称
- `PROJECT_VERSION` -- 项目版本
- `FIRMWARE_NAME` -- 设备名称
- `FIRMWARE_VERSION` -- 固件版本

#### Settings

> 该模块为配置参数的读写模块
> 
> 目前主要分为三个大块配置信息:
> 
> - 云服务连接参数(`cloud`) -- `settings_cloud.py`
> - 定位模块配置参数(`loc`) -- `settings_loc.py`
> - 业务功能配置参数(`user`) -- `settings_user.py`

##### 实例化对象

**示例:**

```python
from settings import Settings

config_file = "/usr/tracker_config.json"
settings = Settings(config_file=config_file)
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|config_file|str|全路径配置参数文件|

##### read

> 读取指定模块的配置信息。

**示例:**

```python
cloud_cfg = settings.read("cloud")
# {"product_key": "xxx", "product_secret": "xxx", "device_name": "xxx", "device_secret": "xxx", "server": "iot-as-mqtt.cn-shanghai.aliyuncs.com", "qos": 1}
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|key|str|参数模块标识, `cloud`, `loc`, `user`, 当不穿是, 返回所有配置参数。|

**返回值:**

|数据类型|说明|
|:---|---|
|dict| 模块参数数据, 获取失败返回None|

##### save

> 存储指定模块的配置信息。

**示例:**

```python
cloud_cfg = {
    "product_key": "xxx",
    "product_secret": "xxx",
    "device_name": "xxx",
    "device_secret": "xxx",
    "server": "iot-as-mqtt.cn-shanghai.aliyuncs.com",
    "qos": 1
}
res = settings.save({"cloud": cloud_cfg})
# True
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|data|dict|指定模块的配置参数。|

**返回值:**

|数据类型|说明|
|:---|---|
|bool|`True` - 成功<br>`False` - 失败|

### settings_cloud

> 该模块用于配置服务端连接参数

#### AliCloudConfig

> 阿里云连接配置参数

| 参数 | 类型 | 说明 |
|---|---|---|
| product_key | str | 产品标识ProductKey |
| product_secret | str | 可选参数，默认为None，productSecret，产品密钥 一机一密认证方案时，此参数传入None 一型一密认证方案时，此参数传入真实的产品密钥 |
| device_name | str | DeviceName,设备名称 |
| device_secret | str | DeviceSecret,可选参数,默认为None，设备密钥（一型一密认证方案时此参数传入None） |
| server | str | 可选参数,需要连接的服务器名称,默认为"iot-as-mqtt.cn-shanghai.aliyuncs.com" |
| qos | int | 消息服务质量(0~1) |

#### ThingsBoardConfig

> ThingsBoard 平台连接配置参数

|参数|类型|说明|
|---|---|---|
|host|str|服务端IP|
|port|int|服务端端口|
|username|str|用户名|
|qos|int|消息服务质量(0~1)|
|client_id|str|客户端id, 可使用设备IMEI号|

### settings_loc

> 定位模块相关配置，GPS，基站，WIFI初始化配置参数，定位方式，坐标系统，GPS模块类型。

#### LocConfig

> 定位模块配置参数列表

| 参数 | 类型| 说明 |
|---|---|---|
|profile_idx|int| PDP索引，ASR平台范围1-8，展锐平台范围1-7，默认1。 |
|\_gps_cfg|dict| 外置GPS UART 串口配置参数 |
|\_cell_cfg|dict| 基站定位配置参数 |
|\_wifi_cfg|dict| WIFI定位配置参数。 |
|map_coordinate_system|str| GPS坐标系统,WGS84,GCJ02 |
|gps_sleep_mode|int| 休眠模式 |

> 字典类型数据说明与样例

\_gps_cfg

| 参数       | 类型   | 说明                                         |
|---------- |--------   |-----------------------------------------  |
| UARTn     | int       | UART串口号，默认1                          |
| buadrate  | int       | 波特率                                     |
| databits  | int       | 数据位（5 ~ 8），展锐平台当前仅支持8位       |
| parity    | int       | 奇偶校验（0 – NONE，1 – EVEN，2 - ODD）     |
| stopbits  | int       | 停止位（1 ~ 2）                            |
| flowctl   | int       | 硬件控制流（0 – FC_NONE， 1 – FC_HW）       |
| gps_mode  | int       | GPS模块类型,0 - 无,1 - 内置GPS,2 - 外置GPS  |
| nmea      | int       | NMEA匹配标识                               |
| PowerPin  | obj       | GNSS PowerKey引脚                          |
| StandbyPin| obj       | GNSS Standby引脚                           |
| BackupPin | obj       | GNSS BackUp引脚                            |

**示例:**

```json
{
    "UARTn": 1,
    "buadrate": 115200,
    "databits": 8,
    "parity": 0,
    "stopbits": 1,
    "flowctl": 0,
    "gps_mode": 1,
    "nmea": 0b010111,
    "PowerPin": null,
    "StandbyPin": null,
    "BackupPin": null,
}
```

\_cell_cfg

| 参数        | 类型  | 说明                                                                    |
|------------   |---------- |---------------------------------------------------------------------  |
| serverAddr    | STRING    | 服务器域名，长度必须小于255 bytes，目前仅支持 “www.queclocator.com”     |
| port          | INT       | 服务器端口，目前仅支持 80 端口                                         |
| token         | STRING    | 密钥，16位字符组成，需要申请                                           |
| timeout       | INT       | 设置超时时间，范围1-300s，默认300s                                    |
| profileIdx    | INT       | PDP索引，ASR平台范围1-8，展锐平台范围1-7                                |

样例:

```json
{
    "serverAddr": "www.queclocator.com",
    "port": 80,
    "token": "XXX",
    "timeout": 3,
    "profileIdx": 1
}
```

\_wifi_cfg

| 参数        | 类型  | 说明                                                                    |
|------------   |---------- |---------------------------------------------------------------------  |
| token         | STRING    | 密钥，16位字符组成，需要申请                                           |

样例:

```json
{
    "token": "XXX"
}
```

> 定位配置参数枚举值

LocConfig.\_gps_mode GPS模块类型列表

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| internal | 0x1 | 内置GPS |
| external | 0x2 | 外置GPS |

LocConfig.\_map_coordinate_system GPS坐标系统

| KEY | VALUE | 说明 |
|---|---|---|
| WGS84 | WGS84 | WGS84 |
| GCJ02 | GCJ02 | GCJ02 |

LocConfig.\_gps_sleep_mode GPS休眠模式

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| pull_off | 0x1 | 断电休眠模式，功耗最低，启动时间长（目前只适用L76K模块） |
| backup | 0x2 | Backup休眠模式，功耗一般，启动时间中等（目前只适用L76K模块） |
| standby | 0x3 | Standby休眠模式，功耗稍高，启动时间快（目前只适用L76K模块） |

### settings_user

> 该模块用于配置业务信息

#### UserConfig

> 业务配置参数枚举值

UserConfig.\_cloud 云服务指定参数

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| AliYun | 0x1 | 阿里云 |
| ThingsBoard | 0x2 | ThingsBoard |

UserConfig.\_loc_method 定位方式列表, 可指定多种定位方式

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| gps | 0x1 | GPS |
| cell | 0x2 | CELL |
| wifi | 0x4 | WIFI |
| all | 0x7 | GPS & CELL & WIFI |

UserConfig.\_work_mode 工作模式

| KEY | VALUE | 说明 |
|---|---|---|
| cycle | 0x1 | 周期性上报 |
| intelligent | 0x2 | 智能模式 |

UserConfig.\_drive_behavior_code 驾驶行为模式

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| sharply_start | 0x1 | 急起 |
| sharply_stop | 0x2 | 急停 |
| sharply_turn_left | 0x3 | 急速左转 |
| sharply_turn_right | 0x4 | 急速右转 |

UserConfig.\_ota_upgrade_status OTA升级状态

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| to_be_updated | 0x1 | 等待升级 |
| updating | 0x2 | 升级中 |
| update_successed | 0x3 | 升级成功 |
| update_failed | 0x4 | 升级失败 |

UserConfig.\_ota_upgrade_module OTA升级模块

| KEY | VALUE | 说明 |
|---|---|---|
| none | 0x0 | 无 |
| sys | 0x1 | 固件 |
| app | 0x2 | 软件 |

> 业务功能参数

| 参数 | 类型 | 说明 |
|---|---|---|
|debug|int|0 - 关闭debug, 1 - 开启debug, 默认: 1|
|log_level|int|日志等级, 默认: `debug`|
|checknet_timeout|int|注网超时时间|
|cloud|int|使用的服务端平台, 默认: `_cloud.AliYun`|
|phone_num|str|电话号码, 默认: `""`|
|low_power_alert_threshold|int|低电告警阈值, 默认: 20|
|low_power_shutdown_threshold|int|低电告警关机, 默认: 5|
|over_speed_threshold|int|超速告警阈值, 默认: 50|
|sw_ota|int|是否开启OTA, 0 - 否, 1 - 是, 默认: 1|
|sw_ota_auto_upgrade|int|是否开启自动OTA, 0 - 否, 1 - 是, 默认: 1|
|sw_voice_listen|int|是否开启语音监听, 0 - 否, 1 - 是, 默认: 0|
|sw_voice_record|int|是否开启语音录制, 0 - 否, 1 - 是, 默认: 0|
|sw_fault_alert|int|是否开启异常告警, 0 - 否, 1 - 是, 默认: 1|
|sw_low_power_alert|int|是否开启低电告警, 0 - 否, 1 - 是, 默认: 1|
|sw_over_speed_alert|int|是否开启超速告警, 0 - 否, 1 - 是, 默认: 1|
|sw_sim_abnormal_alert|int|是否开启SIM卡异常告警, 0 - 否, 1 - 是, 默认: 1|
|sw_disassemble_alert|int|是否开启拆卸告警, 0 - 否, 1 - 是, 默认: 0|
|sw_drive_behavior_alert|int|是否开启异常驾驶行为告警, 0 - 否, 1 - 是, 默认: 0|
|drive_behavior_code|int|异常驾驶行为, 默认: `_drive_behavior_code.none`|
|loc_method|int|定位方式, 默认: `_loc_method.all`|
|loc_gps_read_timeout|int|GNSS定位超时时间, 默认: 300|
|work_mode|int|工作模式, 默认: `_work_mode.cycle`|
|work_mode_timeline|int|智能工作模式阈值, 默认: 3600|
|work_cycle_period|int|上报定位周期, 默认: 60|
|user_ota_action|int|用户升级指令, 默认: -1|
|ota_status|int|OTA升级状态<br>sys_current_version - 当前固件版本<br>sys_target_version - 升级目标固件版本<br>app_current_version - 当前软件版本<br>app_target_version - 软件目标版本<br>upgrade_module - 升级模块<br>upgrade_status - 升级状态|

### tacker_ali

> 阿里云 Tracker 业务功能

#### Tracker

> 业务功能模块, 负责设备的数据采集与上报, 设备功能控制等

##### 实例化对象

**示例:**

```python
from tracker_ali import Tracker

tracker = Tracker()
```

##### add_module

> 添加基础功能模块

**示例:**

```python
from battery import Battery

battery = Battery()

tracker.add_module(battery)
# True
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|module|obj|功能模块对象|

**返回值:**

|数据类型|说明|
|:---|---|
|bool| `True` - 成功, `False` - 失败|

##### running

> 启动业务功能代码

**示例:**

```python
tracker.running()
```

**参数:**

无

**返回值:**

无

##### cloud_callbackɛ

> 用于接收云端下行数据

**示例:**

```python
from aliyunIot import AliYunIot
cloud_cfg = {...}
cloud = AliYunIot(**cloud_cfg)
cloud.set_callback(tracker.cloud_callback)
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|args|tuple|元组数据, 数据格式: `(topic, data)`|

**返回值:**

无

##### net_callback

> 用于接收网络状态变化数据

**示例:**

```python
from net_manage import NetManage
args = (...)
net_manage = NetManage(*args)
net_manage.set_callback(tracker.net_callback)
```

**参数:**

|参数|类型|说明|
|:---|---|---|
|args|tuple|元组数据, 数据格式: `(PDP上下文ID, 网络状态(0表示网络断开，1表示网络连接成功))`|

**返回值:**

无

### tacker_tb

> ThingsBoard Tracker 业务功能, 接口与功能与阿里云一致。
