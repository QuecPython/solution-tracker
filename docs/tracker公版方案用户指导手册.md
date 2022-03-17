# Tracker API v2.0.0

## Tracker

### 创建 Tracker 对象

1. 导入Tracker模块
2. 创建Tracker对象

- 例:

```python
from usr.tracker import Tracker
tracker = Tracker()
```

### battery 电池功能

改功能提供`energy`方法查询当前电池电量。

>`tracker.battery.energy`

- 例:

```python
battery_energy = tracker.battery.energy()
```
- 参数:

无

- 返回值:

返回当前电池电量百分比, 数据类型为`int`。

### locator 定位功能

该功能提供了`read`查询当前模块的定位信息, 定位模式, 定位方式, 定位信息上报模式在`settings`模块中配置, 亦可通过云端远程进行消息控制。

#### `read` 查询当前模块的定位信息。

>`tracker.locator.read`

- 例:

```python
location_info = tracker.locator.read()
```

- 参数:

无

- 返回值:

返回当前定位方式与定位信息, 数据类型为元组, `(loc_method, loc_data)`, `()`空元组表示没有获取到定位信息。

- `loc_method` 定位方式
    - 0 -- 无
    - 1 -- GPS
    - 2 -- 基站
    - 4 -- WIFI(暂不支持)
    - 7 -- GPS&基站&WIFI

- `loc_data` 定位信息
    - `loc_method` -- 1
        - `['GxRMC,XXX...', 'GxGGA,XXX...', 'GxVTG,XXX...']`
    - `loc_method` -- 2
        - `['LBS']`
    - `loc_method` -- 4
        - `[]`

### remote 信息通信功能

#### `post_data` 向云端进行消息发送功能。

- `post_data`发放支持阻塞和非阻塞两种消息发送模式, 默认为阻塞方式进行消息发送。

>`tracker.remote.post_data`

- 例:

```python
import utime
data = {
    'power_switch': True,
    'energy': tracker.battery.energy(),
    'local_time': utime.mktime(utime.localtime())
}
tracker.remote.post_data(tracker.remote.DATA_NON_LOCA, data)
```

- 参数:

|参数|参数类型|参数说明|
|:---|---|---|
|data_type|int|数据类型|
|data|dict|数据信息|

- data_type 枚举值

|枚举值|标识符|说明|
|:---|---|---|
|0|`DATA_NON_LOCA`|非定位数据|
|1|`DATA_LOCA_NON_GPS`|非GPS定位数据|
|2|`DATA_LOCA_GPS`|GPS定位数据|

- 属性功能定义标识符

|功能名称|标识符|数据类型|数据定义|功能描述|读写类型|
|:---|:---|:---|:---|:---|:---|
|开关机|`power_switch`|`bool`|`True`:开启,`False`:关闭||读写|
|电量|`energy`|`int`|取值范围：0 ~ 100||只读|
|电话号码|`phone_num`|`text`|数据长度：11||读写|
|定位方式|`loc_method`|`int`|取值范围：0 ~ 7|0: 无;1: GPS;2: 基站;4: WIFI(暂不支持);7: 全部支持|读写|
|定位工作模式|`loc_mode`|`int`|取值范围：0 ~ 15|0: 无;1: 循环;2: 报警时;4: 电话呼入;8: 开启录音时;15: 全部|读写|
|定位周期|`loc_cycle_period`|`int`|取值范围： ~|单位s|读写|
|本地时间|`local_time`|`int`|取值范围： ~||只读|
|低电报警阈值|`low_power_alert_threshold`|`int`|取值范围：5 ~ 30||读写|
|低电关机阈值|`low_power_shutdown_threshold`|`int`|取值范围：5 ~ 30||读写|
|OTA功能开关|`sw_ota`|`bool`|`True`:开启,`False`:关闭||读写|
|OTA自动升级功能开关|`sw_ota_auto_upgrade`|`bool`|`True`:开启,`False`:关闭||读写|
|语音监听功能开关|`sw_voice_listen`|`bool`|`True`:开启,`False`:关闭||读写|
|录音上报功能开关|`sw_voice_record`|`bool`|`True`:开启,`False`:关闭||读写|
|故障报警功能开关|`sw_fault_alert`|`bool`|`True`:开启,`False`:关闭||读写|
|低电报警功能开关|`sw_low_power_alert`|`bool`|`True`:开启,`False`:关闭||读写|
|超速报警功能开关|`sw_over_speed_alert`|`bool`|`True`:开启,`False`:关闭||读写|
|拔卡报警功能开关|`sw_sim_out_alert`|`bool`|`True`:开启,`False`:关闭||读写|
|拆卸报警功能开关|`sw_disassemble_alert`|`bool`|`True`:开启,`False`:关闭||读写|
|驾驶行为报警功能开关|`sw_drive_behavior_alert`|`bool`|`True`:开启,`False`:关闭||读写|
|驾驶行为代码|`drive_behavior_code`|`int`|取值范围：40001 ~ 40004|40001: quick_start;40002: quick_stop;40003: quick_turn_left;40004: quick_turn_right|只读|
|模块重启|`power_restart`|`bool`|`True`:重启,`False`:无动作||读写|
|超速报警阈值|`over_speed_threshold`|`int`|取值范围：0 ~ 132|单位km/h|读写|
|故障代码|`fault_code`|`int`|取值范围：20001 ~ 29999|20001: net_error,20002: gps_error,20003: temp_sensor_error,20004: light_sensor_error,20005: move_sensor_error,20006: mike_error|只读|
|GPS模块类型|`gps_mode`|`int`|取值范围：0 ~ 2|0: 无GPS模块,1: 内置GPS模块,2: 外置GPS模块|只读|
|是否OTA升级|`user_ota_action`|`bool`|`True`:接受升级,`False`:拒绝升级||只写|
|OTA升级状态|`ota_status`|`int`|取值范围：0 ~ 5|0: 无升级;1: 待升级;2: 升级中;3: 升级成功;4: 升级失败|只读|

- 事件功能定义标识符

|功能名称|标识符|数据定义|
|:---|:---|:---|
|SOS报警|`sos_alert`|`{'local_time': xxx}`|
|故障报警|`fault_alert`|`{'local_time': xxx, 'fault_code': 20001}`|
|低电报警|`low_power_alert`|`{'local_time': xxx, 'energy': 20}`|
|拔卡报警|`sim_out_alert`|`{'local_time': xxx}`|
|驾驶行为报警|`drive_behavior_alert`|`{'local_time': xxx, 'drive_behavior_code': 40001}`|
|拆卸报警|`disassemble_alert`|`{'local_time': xxx}`|
|超速报警|`over_speed_alert`|`{'local_time': xxx}`|

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

#### `set_block_io` 设置消息发送为阻塞或非阻塞方式。

>`tracker.remote.set_block_io`

- 例:

```python
res = tracker.remote.set_block_io(False)
```

- 参数:

|参数|参数类型|参数说明|
|:---|---|---|
|val|bool|是否阻塞发送消息(True:阻塞;False:非阻塞), 默认True。|

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

### alert_report 告警功能

该功能提供`alert_report`方法, 将定义好的报警编码与报警信息上报到云端。

>`tracker.alert_report`

- 例:

```python
import utime
alert_code = 20000
alert_info = {
    'fault_code': 20001,
    'local_time': utime.mktime(utime.localtime())
}
res = tracker.alert_report(alert_code, alert_info)
```

- 参数:

|参数|参数类型|参数说明|
|:---|---|---|
|alert_code|int|报警编码|
|alert_info|dict|报警信息, key为标识符, value为具体信息|

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

- 报警编码与标识符

|报警编码|子码|标识符|说明|
|:---|:---|:---|:---|
|20000|-|`fault_alert`|故障报警|
|-|20001|`net_error`|网络异常|
|-|20002|`gps_error`|GPS异常|
|-|20003|`temp_sensor_error`|温度传感器异常|
|-|20004|`light_sensor_error`|照度传感器异常|
|-|20005|`move_sensor_error`|三轴加速度传感器异常|
|-|20006|`mike_error`|麦克风异常|
|30002|-|`low_power_alert`|低电量报警|
|30003|-|`over_speed_alert`|超速报警|
|30004|-|`sim_out_alert`|拔卡报警|
|30005|-|`disassemble_alert`|拆卸报警|
|40000|-|`drive_behavior_alert`|驾驶行为监测报警|
|-|40001|`quick_start`|急起|
|-|40002|`quick_stop`|急停|
|-|40003|`quick_turn_left`|左急转弯|
|-|40004|`quick_turn_right`|右急转弯|
|50001|-|`sos_alert`|SOS求救报警|

### `loc_report` 用于立即向云端报告设备定位信息功能。

>`tracker.loc_report`

- 例:

```python
res = tracker.loc_report()
```

- 参数:
无

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

### machine_info_report 机器信息上报功能

该模块实现了机器信息的汇总上报功能, 会将机器的位置信息, 开机状态, 电池电量等相关设置信息全部实时上报云端。

- 例:

```python
res = tracker.machine_info_report()
```

- 参数:

无

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

### machine_check 机器自检功能

该功能用于检测设备相关功能是否正常, 主要包括网络状态, GPS模组, 各类传感器, 麦克风是否正常工作(目前暂不支持各类传感器麦克风等外设检测)。 如异常会上报远端异常信息。 检查完毕后不论异常与否都会调用`machine_info_report`功能上报云端设备所有信息。

- 例:

```python
res = tracker.machine_check()
```

- 参数:

无

- 返回值:

返回码，数值类型`int`

|返回码|说明|
|:---|:---|
|0|无异常|
|20001|网络异常|
|20002|GPS异常|
|20003|温度传感器异常|
|20004|照度传感器异常|
|20005|三轴加速度传感器异常|
|20006|麦克风异常|

## settings

该模块为配置参数模块

- 该模块主要有`app`和`sys`两种类型的参数。
- `app`为可修改控制相关参数;
- `sys`为系统默认参数, 不可修改。
- 配置参数都已集成到一个字典中, 可通过`settings.get()`方式获取到具体配置参数
- `app`配置参数具体含义见`quec_cloud_module.json`(导入移远云产品功能定义中)

### settings 导入

- 例:

```python
from usr.settings import settings
```

### init 初始化

- 例:

```python
res = settings.init()
```

- 参数:

无

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

### get 获取配置参数

- 例:

```python
current_settings = settings.get()
```

- 参数:

无

- 返回值:

|返回数据类型|说明|
|:---|---|
|dict|字典参数|

```json
{
    "app": {
        "loc_cycle_period": 1,
        "phone_num": "",
        "loc_method": 1,
        "loc_mode": 0,
        "low_power_alert_threshold": 20,
        "low_power_shutdown_threshold": 5,
        "sw_over_speed_alert": true,
        "over_speed_threshold": 120,
        "sw_disassemble_alert": true,
        "sw_fault_alert": true,
        "sw_low_power_alert": true,
        "sw_voice_record": false,
        "sw_voice_listen": false,
        "sw_sim_out_alert": true,
        "gps_mode": 2,
        "sw_drive_behavior_alert": true,
        "sw_ota": true,
        "sw_ota_auto_upgrade": true
    },
    "sys": {
        "cloud": 1,
        "profile_idx": 1,
        "cloud_init_params": {
            "DK": "XXXXX",
            "DS": "XXXXX",
            "PK": "XXXXX",
            "PS": "XXXXX"
        },
        "locator_init_params": {
            "gps_cfg": {
                "parity": 0,
                "stopbits": 1,
                "flowctl": 0,
                "UARTn": 1,
                "buadrate": 115200,
                "databits": 8
            }
        }
    }
}
```

### set 设置配置参数

- 例:

```python
opt = 'phone_num'
val = '123456789'
res = settings.set(opt, val)
```

- 参数:

|参数|参数类型|参数说明|
|:---|---|---|
|opt|str|配置参数标识符|
|val|str/bool/int|配置参数属性值|

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

- 配置参数标识符列表，见`移远云物模型属性功能定义标识符`表中可写权限数据

### save 持久化保存配置参数

- 例:

```python
res = settings.save()
```

- 参数:

无

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。

### reset 重置配置参数

- 例:

```python
res = settings.reset()
```

- 参数:

无

- 返回值:

返回`bool`类型数据, `True`成功, `False`失败。
