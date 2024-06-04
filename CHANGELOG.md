# ChangeLog

All significant changes to this project will be documented in this file.

## [v2.0.0] - 2024-06-04

### Added

- Restructured the entire Tracker's business functions, adding three new modules: `tracker_collector` (collector), `tracker_controller` (controller), and `tracker_devicecheck` (device status checker).
- Extracted non-business functionalities into separate, independent modules housed within the standalone `modules` project.
- Included sample JSON files for Aliyun and QuecCloud IoT device models.
- **net_manage.py**: Introduced a network management module;
- **power_manage.py**: Added a low-power management module, replacing the previous `mpower.py`;
- **thingsboard.py**: Incorporated MQTT client code for connecting to the ThingsBoard platform;

### Changed

- Refined the overall project architecture, dedicating individual modules to specific platform functionalities (e.g., `tracker_ali.py` for Aliyun, `tracker_tb.py` for ThingsBoard).
- Optimized code within several modules, including:
    + **aliyunIot.py**
    + **battery.py**
    + **buzzer.py**
    + **common.py**
    + **led.py**
    + **location.py**
    + **logging.py**

### Removed

- Removed the ota module as OTA upgrade capabilities are now integrated into respective cloud functionality modules.
- Discontinued the timer module; LED blinking functionality previously in the timer module has been moved to the LED module.
- Decommissioned the Tracker class in the tracker module, redistributing its functionalities among `tracker_collector`, `tracker_controller`, and `tracker_devicecheck`.
- Refactored the SelfCheck function into `tracker_devicecheck`.
- Migrated Aliyun, QuecCloud IoT, battery, common, history, LED, location, logging, and cloud interaction middleware modules into the `modules` directory.
- Retired the QuecCloud module.
- Eliminated the `remote` middleware module.

## [v1.0.0] - 2024-06-04

### Initial Release

- Initial release for this project.