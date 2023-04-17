# ChangeLog

此项目的所有显着更改都将记录在此文件中。

## [v2.1.0] - 2022-05-09

### Added

- `settings_xxx`, 按模块将配置文件进行分类
- 整个Tracker的业务功能进行了结构上的重构，新增了三个模块`tracker_collector`采集器, `tracker_controller`控制器, `tracker_devicecheck`设备状态检测
- 将非业务功能进行了抽离，独立成单独的模块，与业务解耦，独立出`modules`项目，存储独立的功能模块
- 添加阿里云移远云物模型json样例文件

### Changed

- 整个项目的结构进行调整，采用了观察者模式的设计方案对各个模块进行重构。
- Tracker业务只将各个独立的功能模块进行拼接后，在`tracker_collector`中做业务处理
- 原settings_app, settings_sys模块修改为不同的模块，不同的`settings_xx`，进行了分类

### Removed

- 移除了ota模块，ota升级功能已分别集成到不同的云模块功能中
- 移除了timer模块，原timer模块中的LED定时闪烁功能已移至LED功能中
- 移除了tracker模块中的Tracker类功能，将其分类到`tracker_collector`采集器, `tracker_controller`控制器, `tracker_devicecheck`设备状态检测单个模块中
- 移除了tracker模块中的SelfCheck功能，将其重构为`tracker_devicecheck`
- 阿里云，移远云，电池模块，公共模块，历史文件模块，LED模块，定位模块，日志模块，云端交互中间层模块都移入`modules`模块

## [v2.0.0] - 2022-03-15

### Added

- 添加了Tracker整个项目的功能代码，tracker业务模块，阿里云模块，移远云模块，电池模块，公共模块，LED模块，定位模块，日志模块，低功耗模块，OTA模块，云端交互中间层模块，传感器模块，定时器模块，配置模块

## [v2.2.0] - 2023-04-14

### Added

- **net_manage.py**, 添加网络功能管理模块;
- **power_manage.py**, 添加低功耗管理功能模块, 用于替换之前的`mpower.py`;
- **thingsboard.py**, 添加对接ThingsBoard平台MQTT协议客户端代码;

### Changed

- 整个项目架构进行调整, 单个平台单个业务功能逻辑, 如阿里云则对应`tracker_ali.py`, ThingsBoard平台则对应`tracker_tb.py`;
- 优化模块功能代码, 优化模块有:
    + **aliyunIot.py**
    + **battery.py**
    + **buzzer.py**
    + **common.py**
    + **led.py**
    + **location.py**
    + **logging.py**

### Removed

- 移除了移远云模块
- 移除`remote`中间件模块
