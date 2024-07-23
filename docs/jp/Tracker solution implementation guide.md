[中文](../zh/定位器方案应用指导.md) | [English](../en/Tracker%20solution%20implementation%20guide.md) | **日本語** |

# トラッカーソリューションアプリケーションノート

## はじめに

このドキュメントは、提供されたトラッカーソリューションプログラムをモジュールやデバイス上で実行する方法を紹介します。このドキュメントで示される操作は、Quectel EG915Uシリーズモジュールに基づいています。

## ソリューションリソースの取得

トラッカーソリューションリソースは、[https://github.com/QuecPython/solution-tracker](https://github.com/QuecPython/solution-tracker)からダウンロードできます。

> ソリューションプロジェクトには`modules`というサブプロジェクトがあります。サブプロジェクトも一緒にダウンロードすることを忘れないでください。
>
> サブプロジェクトを同期してダウンロードするコマンド：`git clone --recursive https://github.com/QuecPython/solution-tracker.git`

リソースパッケージディレクトリ：

![solution-tracker-001](./media/solution-tracker-001.png)

- *code*

このディレクトリにはソフトウェアソリューションコードが含まれています。

![solution-tracker-002](./media/solution-tracker-002.png)

- *docs*

このディレクトリには、ユーザーガイドや機能インターフェース仕様などのプロジェクトドキュメントが含まれています。

![solution-tracker-003](./media/solution-tracker-003.png)

- *object_model_demo*

このディレクトリには、Alibaba IoTプラットフォームのTSLモデルファイルが含まれており、Alibaba IoTプラットフォームに直接インポートしてデバッグに使用できます。

## ソリューション概要

これはトラッカーソリューションのパブリックバージョンであり、すべての機能を含んでいるわけではありません。このソリューションは、トラッカーのコアコンポーネントの機能実装と、サーバーとのデータインタラクション、イベント転送などの機能を提供します。このフレームワークに基づいてビジネス機能を開発することができます。現在のソフトウェアフレームワークには以下の機能があります：

- MQTTプロトコルを介したデータインタラクション（現在、Alibaba IoTプラットフォームとThingsBoardがサポートされています。）
- 構成ファイルの読み書き
- OTAアップグレード
- LEDインジケーター
- デバイスネットワーク管理
- デバイス情報管理
- バッテリーレベルと充電管理
- バックアップデータストレージ
- GNSS位置特定/基準局位置特定/Wi-Fi位置特定
- 低消費電力管理
- ログの保存と記録

## 環境のセットアップ

### USBドライバーのインストール

デバッグするモジュールのプラットフォームに応じてドライバーをダウンロードしてインストールしてください。[ここをクリックしてUSBドライバーをダウンロード](https://python.quectel.com/download)

![solution-tracker-004](./media/solution-tracker-004.png)

### 開発およびデバッグツールのダウンロード

開発およびデバッグにはQPYcomを使用することをお勧めします。このドキュメントで説明されるプロセスは、QPYcomが使用され、USBドライバーのインストールが成功していることを前提としています。

[ここをクリックしてQPYcomをダウンロード](https://python.quectel.com/download)

![solution-tracker-005](./media/solution-tracker-005.png)

[QPYcomユーザーガイドを表示するにはここをクリック](https://python.quectel.com/doc/Application_guide/en/dev-tools/QPYcom/qpycom-gui.html)

### コード構成パラメーターの変更

現在のソリューションコードで使用されている構成パラメーターは構成されていません。以下の指示に従って構成を変更してください。

*code*フォルダー内の`settings_`で始まる構成ファイルを見つけ、実際のパラメーターに基づいて構成を変更します。以下のように：

- `settings_server.py`は、IoTプラットフォーム接続情報を構成するために使用されます。

```python
class AliIotConfig:

    product_key = ""
    product_secret = ""
    device_name = ""
    device_secret = ""
    server = "iot-as-mqtt.cn-shanghai.aliyuncs.com"
    qos = 1


class ThingsBoardConfig:

    host = ""
    port = 1883
    username = ""
    qos = 0
    client_id = ""
```

- `settings_loc.py`は、位置特定に使用されるモジュールの情報を構成するために使用されます（外部GNSS通信のUARTポート、LBS/Wi-Fi位置特定の認証情報）。

```python
gps_cfg = {
    "UARTn": UART.UART1,
    "buadrate": 115200,
    "databits": 8,
    "parity": 0,
    "stopbits": 1,
    "flowctl": 0,
    "gps_mode": _gps_mode.external,
    "nmea": 0b010111,
    "PowerPin": None,
    "StandbyPin": None,
    "BackupPin": None,
}

cell_cfg = {
    "serverAddr": "www.queclocator.com",
    "port": 80,
    "token": "xxxxxxxxxx",
    "timeout": 3,
    "profileIdx": profile_idx,
}

wifi_cfg = {
    "token": "xxxxxxxxxx"
}
```

- `settings_user.py`は、ユーザービジネス機能に関連するパラメーターを構成するために使用されます（例：アラームスイッチ、低バッテリーレベルのしきい値）。

```python
class _server:
    none = 0x0
    AliIot = 0x1
    ThingsBoard = 0x2

class _drive_behavior_code:
    none = 0x0
    sharply_start = 0x1
    sharply_stop = 0x2
    sharply_turn_left = 0x3
    sharply_turn_right = 0x4

class _ota_upgrade_module:
    none = 0x0
    sys = 0x1
    app = 0x2

debug = 1
log_level = "DEBUG"
checknet_timeout = 60
server = _server.AliIot
phone_num = ""
low_power_alert_threshold = 20
low_power_shutdown_threshold = 5
over_speed_threshold = 50
sw_ota = 1
sw_ota_auto_upgrade = 1
sw_voice_listen = 0
sw_voice_record = 0
sw_fault_alert = 1
sw_low_power_alert = 1
sw_over_speed_alert = 1
sw_sim_abnormal_alert = 1
sw_disassemble_alert = 1
sw_drive_behavior_alert = 1
drive_behavior_code = _drive_behavior_code.none
loc_method = _loc_method.all
loc_gps_read_timeout = 300
work_mode = _work_mode.cycle
work_mode_timeline = 3600
work_cycle_period = 30
user_ota_action = -1
ota_status = {
    "sys_current_version": "",
    "sys_target_version": "--",
    "app_current_version": "",
    "app_target_version": "--",
    "upgrade_module": _ota_upgrade_module.none,
    "upgrade_status": _ota_upgrade_status.none,
}
```

### ファームウェアのダウンロード

現在デバッグしているモジュールモデルに応じて、QuecPython公式サイトから対応するファームウェアをダウンロードし、QPYcomを使用してモジュールにファームウェアをダウンロードします。

[ここをクリックしてファームウェアをダウンロード](https://python.quectel.com/download)

![solution-tracker-006](./media/solution-tracker-006.png)

QPYcomを使用してファームウェアをダウンロードします。

1. ファームウェアを選択

![solution-tracker-007](./media/solution-tracker-007.png)

2. ファームウェアをダウンロード

![solution-tracker-008](./media/solution-tracker-008.png)

3. ファームウェアのダウンロードが完了するまで待ちます

![solution-tracker-009](./media/solution-tracker-009.png)

4. ダウンロードが成功

![solution-tracker-010](./media/solution-tracker-010.png)

5. インタラクティブポートに接続

![solution-tracker-011](./media/solution-tracker-011.png)

6. ダウンロード情報を表示

![solution-tracker-012](./media/solution-tracker-012.png)

### コードのダウンロード

- コードをダウンロードする前に、*`main.py`*ファイルを*`_main.py`*にリネームすることをお勧めします。*`main.py`*ファイルはモジュールが電源を入れると自動的に実行されるため、デバッグには不便です。テスト中は*`_main.py`*ファイルを手動で実行してデバッグを容易にすることができます。

- USB経由でコードをダウンロードする場合、デバイスにUSBポートまたはテストポイントを予約する必要があります。または、EVBを使用してデバッグし、事前にドライバーをインストールします。

1. "**`Quectel USB NMEA PORT`**"を選択します。このシリアルポートはインタラクティブポートであり、QPYcomログもこのシリアルポートを通じて出力されます。

![solution-tracker-013](./media/solution-tracker-013.png)

2. ビジネス機能コードをデバイスにバッチでダウンロードします。 "**Download script**"をクリックし、ダウンロードが完了するまで待ちます。ダウンロードが完了したら、"File"ページで結果を確認します。

![solution-tracker-014](./media/solution-tracker-014.png)

3. ダウンロードが成功したら、デバイスを再起動し、機能を実行することをお勧めします（*`main.py`*ファイルがダウンロードされた場合、デバイスを再起動すると機能が自動的に実行されます。*`main.py`*ファイルを*`_main.py`*にリネームしてからダウンロードした場合、*`_main.py`*ファイルを手動で実行して機能を開始する必要があります）。

![solution-tracker-015](./media/solution-tracker-015.png)

4. 実行結果を表示

![solution-tracker-016](./media/solution-tracker-016.png)
