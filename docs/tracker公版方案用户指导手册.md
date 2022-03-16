# Tracker API v2.0.0

## Tracker

### 创建 Tracker 对象

1. 导入Tracker模块
2. 创建Tracker对象

例:
```python
from usr.tracker import Tracker
tracker = Tracker()
```

### alert 告警功能

该功能提供`post_alert`方法, 将定义好的报警编码与报警信息上报到云端。

>`tracker.alert.post_alert`

例:
```python
import utime
alert_code = 20000
alert_info = {
    'fault_code': 20001,
    'local_time': utime.mktime(utime.localtime())
}
tracker.alert.post_alert(alert_code, alert_info)
```

参数:
|参数|参数类型|参数说明|
|:---|---|---|
|alert_code|int|报警编码|
|alert_info|dict|报警信息, key为标识符, value为具体信息|

返回值:
无

> 报警编码与标识符
> - 20000: `fault_alert`
> - 30002: `low_power_alert`
> - 30003: `over_speed_alert`
> - 30004: `sim_out_alert`
> - 30005: `disassemble_alert`
> - 40000: `drive_behavior_alert`
> - 50001: `sos_alert`
>
>> `fault_alert`故障报警编码与标识符
>> - 20001: `net_error`
>> - 20002: `gps_error`
>> - 20003: `temp_sensor_error`
>> - 20004: `light_sensor_error`
>> - 20005: `move_sensor_error`
>> - 20006: `mike_error`
>
>> `drive_behavior_alert`驾驶行为异常报警编码与标识符
>> - 40001: `quick_start`
>> - 40002: `quick_stop`
>> - 40003: `quick_turn_left`
>> - 40004: `quick_turn_right`

### battery 电池功能

改功能提供`energy`方法查询当前电池电量。

>`tracker.battery.energy`

例:
```python
battery_energy = tracker.battery.energy()
```
参数:
无

返回值:
|返回数据类型|说明|
|:---|---|
|int|电量百分比|

### locator 定位功能

该功能提供了`read`和`trigger`两个方法, 定位模式, 定位方式, 定位信息上报模式在`settings`模块中配置, 亦可通过云端远程进行消息控制。

- `read`方法用于查询当前发送云端的定位信息。
- `trigger`方法用于立即向云端报告设备定位信息功能。

>`tracker.locator.read`

例:
```python
location_info = tracker.locator.read()
```

参数:
无

返回值:
|返回数据类型|元素|说明|
|:---|---|---|
|tuple|||
||0|定位类型(int)|
||1|定位信息(list)|

>`tracker.locator.trigger`

例:
```python
tracker.locator.trigger()
```

参数:
无

返回值:
无

### remote 信息通信功能

该功能提供了`post_data`和`set_block_io`方法向云端进行消息通信功能(目前暂时只支持移远云)。

>`tracker.remote.post_data`

例:
```python
import utime
data = {
    'power_switch': True,
    'energy': tracker.battery.energy(),
    'local_time': utime.mktime(utime.localtime())
}
tracker.remote.post_data(tracker.remote.DATA_NON_LOCA, data)
```

参数:
|参数|参数类型|参数说明|
|:---|---|---|
|data_type|int|数据类型|
|data|dict|数据信息|


返回值:
|返回数据类型|说明|
|:---|---|
|Bool|True:发送成功;False:发送失败|

>`tracker.remote.set_block_io`

例:
```python
tracker.remote.set_block_io(False)
```

参数:
|参数|参数类型|参数说明|
|:---|---|---|
|val|bool|是否阻塞发送消息, 默认True|

- `post_data`方法向云端进行消息发送功能。`post_data`发放支持阻塞和非阻塞两种消息发送模式, 默认为阻塞方式进行消息发送。
- `set_block_io`方法可以设置消息发送的阻塞和非阻塞方式。
- 移远云目前的消息有三种模式
    - `DATA_NON_LOCA` (非位置信息)
    - `DATA_LOCA_NON_GPS` (非GPS位置信息)
    - `DATA_LOCA_GPS` (GPS位置信息)
- 移远云物模型功能定义标识符(具体详述见`quec_cloud_module.json`)
    - `power_switch`
    - `energy`
    - `phone_num`
    - `loc_method`
    - `loc_mode`
    - `loc_cycle_period`
    - `local_time`
    - `low_power_alert_threshold`
    - `low_power_shutdown_threshold`
    - `sw_ota`
    - `sw_ota_auto_upgrade`
    - `sw_voice_listen`
    - `sw_voice_record`
    - `sw_fault_alert`
    - `sw_low_power_alert`
    - `sw_over_speed_alert`
    - `sw_sim_out_alert`
    - `sw_disassemble_alert`
    - `sw_drive_behavior_alert`
    - `drive_behavior_code`
    - `sos_alert`
    - `fault_alert`
    - `low_power_alert`
    - `sim_out_alert`
    - `drive_behavior_alert`
    - `disassemble_alert`
    - `power_restart`
    - `over_speed_threshold`
    - `over_speed_alert`
    - `fault_code`
    - `gps_mode`

### machine_info_report 机器信息上报功能

该模块实现了机器信息的汇总上报功能, 会将机器的位置信息, 开机状态, 电池电量等相关设置信息全部实时上报云端。

例:
```python
tracker.machine_info_report()
```

参数:
无

返回值:
无

### machine_check 机器自检功能

该功能用于检测设备相关功能是否正常, 主要包括网络状态, GPS模组, 各类传感器, 麦克风是否正常工作(目前暂不支持各类传感器麦克风等外设检测)。 如异常会上报远端异常信息。 检查完毕后不论异常与否都会调用`machine_info_report`功能上报云端设备所有信息。

例:
```python
tracker.machine_check()
```

参数:
无

返回值:
无

## settings

该模块为配置参数模块, 该模块主要有`app`和`sys`两种类型的参数。并提供settings方法对`app`类型参数进行修改, 从而实现远程下发指令控制模块功能。

### settings 导入

例:
```python
from usr.settings import settings
```

### init 初始化

例:
```python
settings.init()
```

参数:
无

返回值:
无

### get 获取配置参数

例:
```python
current_settings = settings.get()
```

参数:
无

返回值:
|返回数据类型|说明|
|:---|---|
|dict|字典参数(见下方备注)|

### set 设置配置参数

例:
```python
opt = 'phone_num'
val = '123456789'
settings.set(opt, val)
```

参数:
|参数|参数类型|参数说明|
|:---|---|---|
|opt|str|配置参数标识符|
|val|str/bool/int|配置参数属性值|

返回值:
无

### save 持久化保存配置参数

例:
```python
settings.save()
```

参数:
无

返回值:
无

### reset 重置配置参数

例:
```python
settings.reset()
```

参数:
无

返回值:
无

>备注
- `app`为可修改控制相关参数;
- `sys`为系统默认参数, 不可修改。
- 配置参数都已集成到一个字典中, 可通过`settings.get()`方式获取到具体配置参数
- `app`配置参数具体含义见`quec_cloud_module.json`(导入移远云产品功能定义中)

>settings.get() 返回值
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
