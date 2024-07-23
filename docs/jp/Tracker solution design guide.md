[中文](../zh/定位器方案设计指导.md) | [English](../en/Tracker%20solution%20design%20guide.md) | **日本語** |

# トラッカーソリューション設計ガイド

## はじめに

このドキュメントは、QuecPythonソリューションにおけるQuecelスマートトラッカーの設計フレームワークを説明します。これには、ソフトウェアおよびハードウェアシステムのフレームワーク、主要コンポーネントの説明、システム初期化プロセスおよびビジネスプロセスの紹介と機能例が含まれます。これにより、Quectelスマートトラッカーの全体的なアーキテクチャと機能を迅速に理解するのに役立ちます。

## 機能概要

スマートトラッカーソリューションのソフトウェア機能は、以下の図に示されています。このソリューションは、トラッカーの実際のビジネスに基づいて機能を分割し、モジュール化された方法で開発されています。

![solution-tracker-101](./media/solution-tracker-101.png)

- 伝送プロトコル解析
    + Alibaba IoTプラットフォームとの接続およびデータのやり取り
    + ThingsBoardとの接続およびデータのやり取り
    + GT06プロトコル
    + JT/T808プロトコル
- ネットワーク管理
    + MQTTプロトコル（Alibaba IoT/ThingsBoard/その他のプラットフォーム）
    + TCP/UDPプロトコル（GT06/JTT808プロトコル）
    + APN設定（ネットワーク登録およびデータコール）
    + LTE NET（4Gネットワーク登録およびデータコール）
- 周辺機器管理
    + GNSS：GNSSモジュールのオン/オフ、GNSSモジュールからの位置データの読み取り、およびAGPSデータの注入。
    + Gセンサー：センサーのデータを読み取る
    + 充電IC：充電管理、デバイスの充電状態の取得
    + バッテリー：バッテリー管理、バッテリー電圧の読み取りおよびバッテリーレベルの計算
    + LED：LEDインジケーター
- データストレージ
    + システム構成パラメータの保存
    + 位置データのバックアップ保存
    + AGPSダウンロード保存
    + ログ情報の保存
- デバイスのアップグレード
    + OTAアップグレード
- ビジネス機能管理
    + ネットワークおよびIoTプラットフォームの接続および再接続
    + デバイスデータの取得および報告
    + アラームの検出および報告
    + IoTプラットフォームのダウンリンクコマンドの処理
    + デバイスの低消費電力

## データインタラクションプロセス

モジュールとIoTプラットフォーム間のデータインタラクションプロセスは、以下の図に示されています。

![solution-tracker-102](./media/solution-tracker-102.png)

プロセスの説明：

1. モバイルAPPがコマンドをIoTプラットフォームに送信します。サーバーはTCP/UDP/MQTTプロトコルを介してモジュールにコマンドを発行し、モジュールはコマンドデータを解析します。
2. モジュールはTCP/UDP/MQTTプロトコルを介してデータをIoTプラットフォームに報告します。IoTプラットフォームはデータを処理し、モバイルAPPに同期表示します。

## ソフトウェアフレームワーク

### 設計哲学とパターン

- このシステムはリスナーパターンとして設計されており、コールバック関数を介してメッセージを送信し、イベントをリッスンします。
- ソフトウェア機能はトラッカーのビジネス要件に基づいて分割され、機能モジュールに基づいて実装されています。各部分は独立して開発され、依存関係を減らし、独立してデバッグおよび実行できるため、デカップリング効果を達成します。
- 機能間のインタラクションはコールバック関数を介して実現されます。すべてのビジネス機能の処理（ダウンリンクコマンドの処理、アラームの検出、データの取得および報告、デバイスの制御など）は、`Tracker`クラスで行われます。

![solution-tracker-104](./media/solution-tracker-104.png)

1. すべての機能モジュールは`Tracker`クラスに`Tracker.add_module`を介して登録されます。
2. サーバーモジュール（IoTプラットフォームインタラクションモジュール）は、コールバック関数を介してサービスダウンリンクデータを`Tracker.server_callback()`に送信して処理します。
3. NetManageモジュールは、コールバック関数を介してネットワーク切断イベントを`Tracker.net_callback`に送信して処理します。

### ソフトウェアアーキテクチャ図

ソフトウェアシステムフレームワークは次のように説明されます：

- 表示層、異なるIoTプラットフォームとの接続
- トランスポート層、異なるプロトコルを介したデータインタラクション
- ビジネス層、主にデバイスデータの取得、デバイス制御、IoTプラットフォームのダウンリンクコマンドの受信および処理、データの統合および報告に使用されます。
- デバイス層、位置データの取得および解析、センサーデータの読み取り、バッテリー管理および履歴データの保存、デバイス情報の取得およびデバイス機能の設定（デバイスバージョン、IMEI番号、APN設定、ネットワークデータコール、デバイスの低消費電力など）を含みます。

![solution-tracker-107](./media/solution-tracker-107.png)

## コンポーネントの紹介

### コアビジネスモジュール（Tracker）

1. 機能説明

コアビジネスロジックを実装し、サーバーと対話してデータを解析し、デバイスモジュールを制御します。すべての機能は、ビジネスイベントメッセージキューのサブスレッドでイベントとして渡され、処理されます。

2. 実装原理

- 機能モジュールを登録して、位置情報、バッテリー情報、センサー情報などのさまざまな機能モジュールからデータを取得します。

```python
class Tracker:
    ...

    def add_module(self, module):
        # 機能モジュールをTrackerクラスに登録して、Trackerクラスで制御します
        if isinstance(module, AliIot):
            self.__server = module
        elif isinstance(module, AliIotOTA):
            self.__server_ota = module
        elif isinstance(module, Battery):
            self.__battery = module
        elif isinstance(module, History):
            self.__history = module
        elif isinstance(module, GNSS):
            self.__gnss = module
        elif isinstance(module, CellLocator):
            self.__cell = module
        elif isinstance(module, WiFiLocator):
            self.__wifi = module
        elif isinstance(module, NMEAParse):
            self.__nmea_parse = module
        elif isinstance(module, CoordinateSystemConvert):
            self.__csc = module
        elif isinstance(module, NetManage):
            self.__net_manage = module
        elif isinstance(module, PowerManage):
            self.__pm = module
        elif isinstance(module, TempHumiditySensor):
            self.__temp_sensor = module
        elif isinstance(module, Settings):
            self.__settings = module
        else:
            return False
        return True

    def running(self, args=None):
        if self.__running_tag == 1:
            return
        self.__running_tag = 1
        # デバイスのスリープを無効にする
        self.__pm.autosleep(0)
        self.__pm.set_psm(mode=0)
        # ビジネスイベントメッセージキューのサブスレッドを開始する
        self.__business_start()
        # バージョンOTAアップグレードコマンドをイベントキューに送信して実行する
        self.__business_queue.put((0, "ota_refresh"))
        # 位置データ報告イベントを送信する（ネットワーク接続、デバイスデータの取得および報告を含む）
        self.__business_queue.put((0, "loc_report"))
        # OTAアップグレードのクエリエベントを送信する
        self.__business_queue.put((0, "check_ota"))
        # デバイスのスリープイベントを送信する
        self.__business_queue.put((0, "into_sleep"))
        self.__running_tag = 0
```

- コールバック関数を介してサーバーが発行するコマンドをリッスンし、ビジネス処理を行います。

```python
class Tracker:
    ...

    def server_callback(self, args):
        # サーバーのダウンリンクメッセージをビジネスイベントメッセージキューに渡して処理します
        self.__business_queue.put((1, args))
```

```python
class Tracker:
    ...

    def __business_running(self):
        while True:
            data = self.__business_queue.get()
            with self.__business_lock:
                self.__business_tag = 1
                ...
                # IoTプラットフォームのダウンリンクコマンドを処理します
                if data[0] == 1:
                    self.__server_option(*data[1])
                self.__business_tag = 0
```

```python
class Tracker:
    ...

    def __server_option(self, topic, data):
        if topic.endswith("/property/set"):
            # プロパティ設定のダウンリンクメッセージを処理します
            self.__server_property_set(data)
        elif topic.find("/rrpc/request/") != -1:
            # 透過データのダウンリンクメッセージを処理します
            msg_id = topic.split("/")[-1]
            self.__server_rrpc_response(msg_id, data)
        elif topic.find("/thing/service/") != -1:
            # サービスデータのダウンリンクメッセージを処理します
            service = topic.split("/")[-1]
            self.__server_service_response(service, data)
        elif topic.startswith("/ota/device/upgrade/") or topic.endswith("/ota/firmware/get_reply"):
            # OTAアップグレードのダウンリンクメッセージを処理します
            user_cfg = self.__settings.read("user")
            if self.__server_ota_flag == 0:
                if user_cfg["sw_ota"] == 1:
                    self.__server_ota_flag = 1
                    if user_cfg["sw_ota_auto_upgrade"] == 1 or user_cfg["user_ota_action"] == 1:
                        # OTAアップグレードの条件が満たされた後、OTAアップグレードを実行します
                        self.__server_ota_process(data)
                    else:
                        self.__server_ota_flag = 0
                        self.__server_ota.set_ota_data(data["data"])
                        ota_info = self.__server_ota.get_ota_info()
                        ota_info["ota_status"] = 1
                        self.__server_ota_state_save(**ota_info)
                else:
                    module = data.get("data", {}).get("module")
                    self.__server.ota_device_progress(-1, "Device is not alowed ota.", module)
```

- RTCコールバック関数を介してデバイスをスリープからウェイクアップし、ビジネスデータを報告します。

```python
class Tracker:
    ...

    def __into_sleep(self):
        while True:
            if self.__business_queue.size() == 0 and self.__business_tag == 0:
                break
            utime.sleep_ms(500)
        user_cfg = self.__settings.read("user")
        # スリープ期間に基づいてスリープモード（オートスリープまたはPSM）を自動的に調整します
        if user_cfg["work_cycle_period"] < user_cfg["work_mode_timeline"]:
            self.__pm.autosleep(1)
        else:
            self.__pm.set_psm(mode=1, tau=user_cfg["work_cycle_period"], act=5)
        # 指定された時間にデバイスをウェイクアップするためにRTCを有効にします
        self.__set_rtc(user_cfg["work_cycle_period"], self.running)

    def __set_rtc(self, period, callback):
        # デバイスをウェイクアップするためにRTCを設定します
        self.__business_rtc.enable_alarm(0)
        if callback and callable(callback):
            self.__business_rtc.register_callback(callback)
        atime = utime.localtime(utime.mktime(utime.localtime()) + period)
        alarm_time = (atime[0], atime[1], atime[2], atime[6], atime[3], atime[4], atime[5], 0)
        _res = self.__business_rtc.set_alarm(alarm_time)
        log.debug("alarm_time: %s, set_alarm res %s." % (str(alarm_time), _res))
        return self.__business_rtc.enable_alarm(1) if _res == 0 else -1
```

3. 機能モジュールの登録とコールバック関数の設定

```python
def main():
    # ネットワーク管理モジュールを初期化します
    net_manage = NetManage(PROJECT_NAME, PROJECT_VERSION)
    # 構成パラメータモジュールを初期化します
    settings = Settings()
    # バッテリー検出モジュールを初期化します
    battery = Battery()
    # 履歴データモジュールを初期化します
    history = History()
    # IoTプラットフォーム（AliIot）モジュールを初期化します
    server_cfg = settings.read("server")
    server = AliIot(**server_cfg)
    # IoTプラットフォーム（AliIot）OTAモジュールを初期化します
    server_ota = AliIotOTA(PROJECT_NAME, FIRMWARE_NAME)
    server_ota.set_server(server)
    # 低消費電力モジュールを初期化します
    power_manage = PowerManage()
    # 温湿度センサーモジュールを初期化します
    temp_sensor = TempHumiditySensor(i2cn=I2C.I2C1, mode=I2C.FAST_MODE)
    loc_cfg = settings.read("loc")
    # GNSS位置特定モジュールを初期化します
    gnss = GNSS(**loc_cfg["gps_cfg"])
    # LBS位置特定モジュールを初期化します
    cell = CellLocator(**loc_cfg["cell_cfg"])
    # Wi-Fi位置特定モジュールを初期化します
    wifi = WiFiLocator(**loc_cfg["wifi_cfg"])
    # GNSS位置特定データ解析モジュールを初期化します
    nmea_parse = NMEAParse()
    # WGS84からGCJ02への座標系変換モジュールを初期化します
    cyc = CoordinateSystemConvert()

    # トラッカービジネスモジュールを初期化します
    tracker = Tracker()
    # 基本オブジェクトをTrackerクラスに登録して制御します
    tracker.add_module(settings)
    tracker.add_module(battery)
    tracker.add_module(history)
    tracker.add_module(net_manage)
    tracker.add_module(server)
    tracker.add_module(server_ota)
    tracker.add_module(power_manage)
    tracker.add_module(temp_sensor)
    tracker.add_module(gnss)
    tracker.add_module(cell)
    tracker.add_module(wifi)
    tracker.add_module(nmea_parse)
    tracker.add_module(cyc)

    # ネットワークモジュールのコールバック関数を設定し、ネットワークが切断されたときにビジネスを処理します
    net_manage.set_callback(tracker.net_callback)
    # サーバーからのダウンリンクデータを受信するコールバック関数を設定し、サーバーがコマンドを発行したときにビジネスを処理します
    server.set_callback(tracker.server_callback)

    # トラッカープロジェクトのビジネス機能を開始します
    tracker.running()


if __name__ == "__main__":
    # メインファイルを実行します
    main()
```

### 位置特定

1. 機能説明

内蔵または外部のGNSS、LBS、およびWi-Fiを介して現在のデバイスの位置情報を取得します。

2. 実装原理

- GNSSモジュールをオンにして、*quecgnss.read()*を介して内蔵GNSSから位置データを読み取ります。

```python
class GNSS:
    ...

    def __internal_read(self):
        log.debug("__internal_read start.")
        # GNSSをオンにする
        self.__internal_open()

        # シリアルポートにキャッシュされた履歴GNSSデータをクリアする
        while self.__break == 0:
            gnss_data = quecgnss.read(1024)
            if gnss_data[0] == 0:
                self.__break = 1
        self.__break = 0

        self.__gps_nmea_data_clean()
        self.__gps_data_check_timer.start(2000, 1, self.__gps_data_check_callback)
        cycle = 0
        # 生のGNSSデータを読み取る
        while self.__break == 0:
            gnss_data = quecgnss.read(1024)
            if gnss_data and gnss_data[1]:
                this_gps_data = gnss_data[1].decode() if len(gnss_data) > 1 and gnss_data[1] else ""
                self.__reverse_gps_data(this_gps_data)
                if self.__check_gps_valid():
                    self.__break = 1
            cycle += 1
            if cycle >= self.__retry:
                if self.__break != 1:
                    self.__break = 1
            if self.__break != 1:
                utime.sleep(1)
        self.__gps_data_check_timer.stop()
        self.__break = 0

self.__gps_data_check_callback(None)
        # GNSSをオフにする
        self.__internal_close()
        log.debug("__internal_read %s." % ("success" if self.__get_gps_data() else "failed"))
        return self.__get_gps_data()
```

- UARTを介して外部GNSSモジュールから位置データを読み取ります。

```python
class GNSS:
    ...

    def __external_read(self):
        # 外部GNSSモジュールのUARTを開く
        self.__external_open()
        log.debug("__external_read start")

        # UARTにキャッシュされた履歴GNSSデータをクリアする
        while self.__break == 0:
            self.__gps_timer.start(50, 0, self.__gps_timer_callback)
            signal = self.__external_retrieve_queue.get()
            log.debug("[first] signal: %s" % signal)
            if signal:
                to_read = self.__external_obj.any()
                log.debug("[first] to_read: %s" % to_read)
                if to_read > 0:
                    self.__set_gps_data(self.__external_obj.read(to_read).decode())
            self.__gps_timer.stop()
        self.__break = 0

        self.__gps_nmea_data_clean()
        self.__gps_data_check_timer.start(2000, 1, self.__gps_data_check_callback)
        cycle = 0
        # 生のGNSSデータを読み取る
        while self.__break == 0:
            self.__gps_timer.start(1500, 0, self.__gps_timer_callback)
            signal = self.__external_retrieve_queue.get()
            log.debug("[second] signal: %s" % signal)
            if signal:
                to_read = self.__external_obj.any()
                log.debug("[second] to_read: %s" % to_read)
                if to_read > 0:
                    self.__reverse_gps_data(self.__external_obj.read(to_read).decode())
                    if self.__check_gps_valid():
                        self.__break = 1

            self.__gps_timer.stop()
            cycle += 1
            if cycle >= self.__retry:
                self.__break = 1
            if self.__break != 1:
                utime.sleep(1)
        self.__gps_data_check_timer.stop()
        self.__break = 0

        # GPSデータが使用可能かどうかを確認します
        self.__gps_data_check_callback(None)
        # 外部GNSSモジュールのUARTを閉じる
        self.__external_close()
        log.debug("__external_read %s." % ("success" if self.__get_gps_data() else "failed"))
        return self.__get_gps_data()
```

- LBSから位置データ（緯度、経度、精度など）を読み取ります。

```python
class CellLocator:
    ...

    def __read_thread(self):
        loc_data = ()
        try:
            # LBS位置データを読み取る
            loc_data = cellLocator.getLocation(
                self.__serverAddr,
                self.__port,
                self.__token,
                self.__timeout,
                self.__profileIdx
            )
            loc_data = loc_data if isinstance(loc_data, tuple) and loc_data[0] and loc_data[1] else ()
        except Exception as e:
            sys.print_exception(e)
        self.__queue.put(loc_data)
```

- Wi-Fiから位置データ（緯度、経度、精度、MACアドレスなど）を読み取ります。

```python
class WiFiLocator:

    def __init__(self, token):
        self.__wifilocator = wifilocator(token) if wifilocator else None

    def read(self):
        loc_data = -1
        try:
            return self.__wifilocator.getwifilocator() if self.__wifilocator else -1
        except Exception as e:
            sys.print_exception(e)
        return loc_data
```

### バッテリー

1. 機能説明

バッテリーレベルと電圧を読み取ります。バッテリーの充電状態を取得し、コールバック関数を介して状態の変化を通知します。

2. 実装原理

- バッテリー電圧を読み取る方法は2つあります。
    + *Power.getVbatt()*を介して電圧を取得
    + ADCを介して取得した電圧を計算

```python
class Battery(object):
    ...

    def __get_power_vbatt(self):
        """Get vbatt from power"""
        # Power.getVbatt()を介して電圧を取得
        return int(sum([Power.getVbatt() for i in range(100)]) / 100)

    def __get_adc_vbatt(self):
        """Get vbatt from adc"""
        # ADCを介して取得した電圧を計算
        self.__adc.open()
        utime.sleep_ms(self.__adc_period)
        adc_list = list()
        for i in range(self.__adc_period):
            adc_list.append(self.__adc.read(self.__adc_num))
            utime.sleep_ms(self.__adc_period)
        adc_list.remove(min(adc_list))
        adc_list.remove(max(adc_list))
        adc_value = int(sum(adc_list) / len(adc_list))
        self.__adc.close()
        vbatt_value = adc_value * (self.__factor + 1)
        return vbatt_value
```

- バッテリーの状態の計算は現在アナログのみです。以下の電圧、温度、およびバッテリーレベルのデータ関係表に基づいてファジー値を取得できます。

```python
BATTERY_OCV_TABLE = {
    "nix_coy_mnzo2": {
        55: {
            4152: 100, 4083: 95, 4023: 90, 3967: 85, 3915: 80, 3864: 75, 3816: 70, 3773: 65, 3737: 60, 3685: 55,
            3656: 50, 3638: 45, 3625: 40, 3612: 35, 3596: 30, 3564: 25, 3534: 20, 3492: 15, 3457: 10, 3410: 5, 3380: 0,
        },
        20: {
            4143: 100, 4079: 95, 4023: 90, 3972: 85, 3923: 80, 3876: 75, 3831: 70, 3790: 65, 3754: 60, 3720: 55,
            3680: 50, 3652: 45, 3634: 40, 3621: 35, 3608: 30, 3595: 25, 3579: 20, 3548: 15, 3511: 10, 3468: 5, 3430: 0,
        },
        0: {
            4147: 100, 4089: 95, 4038: 90, 3990: 85, 3944: 80, 3899: 75, 3853: 70, 3811: 65, 3774: 60, 3741: 55,
            3708: 50, 3675: 45, 3651: 40, 3633: 35, 3620: 30, 3608: 25, 3597: 20, 3585: 15, 3571: 10, 3550: 5, 3500: 0,
        },
    },
}
```

```python
class Battery:
    ...

    def __get_soc_from_dict(self, key, volt_arg):
        """Get battery energy from map"""
        if BATTERY_OCV_TABLE[self.__battery_ocv].get(key):
            volts = sorted(BATTERY_OCV_TABLE[self.__battery_ocv][key].keys(), reverse=True)
            pre_volt = 0
            volt_not_under = 0  # Determine whether the voltage is lower than the minimum voltage value of soc.
            for volt in volts:
                if volt_arg > volt:
                    volt_not_under = 1
                    soc1 = BATTERY_OCV_TABLE[self.__battery_ocv][key].get(volt, 0)
                    soc2 = BATTERY_OCV_TABLE[self.__battery_ocv][key].get(pre_volt, 0)
                    break
                else:
                    pre_volt = volt
            if pre_volt == 0:  # Input Voltarg > Highest Voltarg
                return soc1
            elif volt_not_under == 0:
                return 0
            else:
                return soc2 - (soc2 - soc1) * (pre_volt - volt_arg) // (pre_volt - volt)

    def __get_soc(self, temp, volt_arg):
        """Get battery energy by temperature and voltage"""
        if temp > 30:
            return self.__get_soc_from_dict(55, volt_arg)
        elif temp < 10:
            return self.__get_soc_from_dict(0, volt_arg)
        else:
            return self.__get_soc_from_dict(20, volt_arg)
```

- バッテリーの充電状態は、ピンを割り込み、ピンの高低を取得することで判断されます。

```python
class Battery:
    ...

    def __update_charge_status(self):
        """Update Charge status by gpio status"""
        if not self.__usb:
            chrg_level = self.__chrg_gpio.read()
            stdby_level = self.__stdby_gpio.read()
            if chrg_level == 1 and stdby_level == 1:
                # Not charge.
                self.__charge_status = 0
            elif chrg_level == 0 and stdby_level == 1:
                # Charging.
                self.__charge_status = 1
            elif chrg_level == 1 and stdby_level == 0:
                # Charge over.
                self.__charge_status = 2
            else:
                raise TypeError("CHRG and STDBY cannot be 0 at the same time!")
        else:
            self.__usb_charge()

    @property
    def charge_status(self):
        """Get charge status
        Returns:
            0 - Not charged
            1 - Charging
            2 - Finished charging
        """
        self.__update_charge_status()
        return self.__charge_status

```

### 電力管理

1. 機能説明

デバイスを定期的にウェイクアップし、ビジネスロジックを処理します。ビジネス処理が完了した後、デバイスはスリープモードに入ります。

現在、2つのスリープモードがサポートされています。

- オートスリープ
- PSM

2. 実装原理

対応するスリープモードを設定してデバイスをスリープモードにし、RTCを介してデバイスをウェイクアップします。

```python
class PowerManage:
    ...

    def autosleep(self, val):
        """Set device autosleep.

        Args:
            val (int): 0 - disable, 1 - enable.

        Returns:
            bool: True - success. False - failed.
        """
        return True if hasattr(pm, "autosleep") and val in (0, 1) and pm.autosleep(val) == 0 else False

    def set_psm(self, mode=1, tau=None, act=None):
        """Set device psm.

        Args:
            mode (int): 0 - disable psm, 1 - enable psm.
            tau (int/None): tau seconds. When mode is 0, this value is None. (default: `None`)
            act (int/None): act seconds. When mode is 0, this value is None. (default: `None`)

        Returns:
            bool: True - success. False - failed.
        """
        if not hasattr(pm, "set_psm_time") or not hasattr(pm, "get_psm_time"):
            return False
        if mode == 0:
            return pm.set_psm_time(0)
        else:
            self.__init_tau(tau)
            self.__init_act(act)
            res = pm.set_psm_time(self.__tau_unit, self.__tau_time, self.__act_unit, self.__act_time)
            log.info("set_psm_time: %s" % res)
            if res:
                get_psm_res = pm.get_psm_time()
                log.debug("get_psm_res: %s" % str(get_psm_res))
                if get_psm_res[0] == 1 and get_psm_res[1:] == [self.__tau_unit, self.__tau_time, self.__act_unit, self.__act_time]:
                    log.debug("PSM time equal set time.")
            return res
```

### AliyunIot

1. 機能説明

MQTTプロトコルを介してAlibaba IoTプラットフォームと対話します。

- プラットフォームへの接続およびログイン
- サーバーにTSLモデルデータを送信
- サーバーからのコマンドを受信
- OTAアップグレードを実行

> ここではAlibaba IoTプラットフォームのMQTTプロトコルを例として取り上げます。実際のアプリケーションは、実際のIoTプラットフォームとプロトコルに基づいて開発されるべきであり、基本的なロジックは同様です。

2. 実装原理

Alibaba IoTプラットフォームにログインし、MQTTプロトコルを介して通信ルールに従って対話します。

- アカウントを登録してログイン

```python
class AliIot:
    ...

    def connect(self):
        res = -1
        self.__server = "%s.%s" % (self.__product_key, self.__domain)
        log.debug("self.__product_key: %s" % self.__product_key)
        log.debug("self.__product_secret: %s" % self.__product_secret)
        log.debug("self.__device_name: %s" % self.__device_name)
        log.debug("self.__device_secret: %s" % self.__device_secret)
        log.debug("self.__server: %s" % self.__server)
        self.__server = aLiYun(self.__product_key, self.__product_secret, self.__device_name, self.__device_secret, self.__server)
        res = self.__server.setMqtt(self.__device_name)
        if res == 0:
            self.__server.setCallback(self.__subscribe_callback)
            res = self.__subscribe_topics()
            if res == 0:
                self.__server.start()
        return res
```

- データを報告

```python
class AliIot:
    ...

    def properties_report(self, data):.
        # プロパティを報告
        _timestamp = self.__timestamp
        _id = self.__id
        params = {key: {"value": val, "time": _timestamp} for key, val in data.items()}
        properties = {
            "id": _id,
            "version": "1.0",
            "sys": {
                "ack": 1
            },
            "params": params,
            "method": "thing.event.property.post",
        }
        pub_res = self.__server.publish(self.ica_topic_property_post, ujson.dumps(properties), qos=self.__qos) if self.__server else -1
        return self.__get_post_res(_id) if pub_res is True else False

    def event_report(self, event, data):
        # イベントを報告
        _timestamp = self.__timestamp
        _id = self.__id
        params = {"value": data, "time": _timestamp}
        properties = {
            "id": _id,
            "version": "1.0",
            "sys": {
                "ack": 1
            },
            "params": params,
            "method": "thing.event.%s.post" % event,
        }
        pub_res = self.__server.publish(self.ica_topic_event_post.format(event), ujson.dumps(properties), qos=self.__qos) if self.__server else -1
        return self.__get_post_res(_id) if pub_res is True else False
```

- ダウンリンクデータに応答

```python
class AliIot:
    ...

    def __subscribe_callback(self, topic, data):
        topic = topic.decode()
        try:
            data = ujson.loads(data)
        except:
            pass
        log.debug("topic: %s, data: %s" % (topic, str(data)))

        if topic.endswith("/post_reply"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 200 else False)
            return
        elif topic.endswith("/thing/ota/firmware/get_reply"):
            self.__put_post_res(data["id"], True if int(data["code"]) == 200 else False)

        if self.__callback and callable(self.__callback):
            # データをTracker.server_callback()に渡して処理します
            self.__callback((topic, data))
```

- OTAアップグレード

```python
class AliIotOTA:
    ...

    def start(self):
        # OTAアップグレードを開始
        if self.__module == self.__project_name:
            self.__start_sota()
        elif self.__module == self.__firmware_name:
            self.__start_fota()
        else:
            return False
        return True

    def __start_fota(self):
        log.debug("__start_fota")
        fota_obj = fota()
        url1 = self.__files[0]["url"]
        url2 = self.__files[1]["url"] if len(self.__files) > 1 else ""
        log.debug("start httpDownload")
        if url2:
            res = fota_obj.httpDownload(url1=url1, url2=url2, callback=self.__fota_callback) if fota_obj else -1
        else:
            res = fota_obj.httpDownload(url1=url1, callback=self.__fota_callback) if fota_obj else -1
        log.debug("httpDownload res: %s" % res)
        if res == 0:
            self.__ota_timer.start(600 * 1000, 0, self.__ota_timer_callback)
            fota_res = self.__fota_queue.get()
            self.__ota_timer.stop()
            return fota_res
        else:
            self.__server.ota_device_progress(-2, "Download File Failed.", module=self.__module)
            return False
```

### UMLクラス図

以下は、プロジェクトソフトウェアコード内のすべてのコンポーネントオブジェクトの依存関係と継承関係を示すUMLクラス図です。"Tracker"はトップレベルのオブジェクトであり、依存するコンポーネントオブジェクトと関連しています。

![solution-tracker-104](./media/solution-tracker-104.png)

## イベントフローの説明

### ビジネスプロセス

![solution-tracker-105](media/solution-tracker-105.png)

ビジネスプロセスの説明：

1. デバイスの電源を入れます。
2. APNを構成し、ネットワークに接続します（ネットワーク登録およびデータコール）。IoTプラットフォームを構成し、接続を確立します。失敗した場合は再試行します。
3. オブジェクトの起動を検出し、データを取得します。
    - GNSSオブジェクトの電源を入れ、位置データを待ちます。
    - Gセンサーをオンにし、キャリブレーションを検出します。
    - LEDインジケーター（ネットワーク状態/位置特定状態/充電状態など）をオンにします。
    - バッテリーレベルを取得し、充電状態を検出します。
    - アラームを検出します（オーバースピード/振動/ジオフェンス/低バッテリーレベルなど）。
4. IoTプラットフォームに接続した後、報告する必要がある履歴データがあるかどうかを確認し、報告します。
5. IoTプラットフォームに正常に接続した後、現在のデバイス情報（位置/アラーム）を報告します。
6. IoTプラットフォームへの接続が失敗した場合、現在のデバイス情報（位置/アラーム）を保存します。
7. デバイスにタスクがない場合、低消費電力モードに入り、定期的にデバイスをウェイクアップしてデバイス情報を検出し、報告します。
8. IoTプラットフォームに接続した後、IoTプラットフォームが発行するコマンドを待ちます。
9. コマンドを解析します。
    - デバイス制御コマンド（デバイスビジネスパ
