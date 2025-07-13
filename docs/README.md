# py_serial_app_for_witmotion

## 概要

このプロジェクトは、Witmotion HWT905 TTL MPU-9250 というセンサーからのデータを非同期シリアル通信で受信し、
リアルタイムでグラフに表示するPythonアプリです。

## 主な機能

- 非同期シリアル通信: asyncioとserial_asyncioを使用したデータ受信
- リアルタイム可視化: matoplotlibとPyQt5をしたリアルタイムグラフ表示
- 角度データ、磁場データ表示: 角度をリアルタイムプロット表示（ロール、ピッチ、ヨー）、磁場の方向と強度を可視化
- 受信データの整合性: データのフォーマットチェック
- 設定管理: シリアルポート、ボーレート、データフォーマットなどの設定を管理

## アーキテクチャ

```
py_serial_app_for_witmotion/
├── apps/
│   └── serial_app.py
├── config/
│   └── config.ini
├── docs/
│   └── READEME.md
├── src/
│   ├── __init__.py
│   ├── constants.py
│   ├── hwt905_ttl_datapatser.py
│   └── serial_communication_async.py
├── tests/
│   └── In preparation
├── logs
├── LICENSE
├── pyproject.toml
├── setup.py
└── .pytest.ini
```

## インストール

### 前提条件

- Python 3.9以上
- Witmotion HWT905 TTL センサー
- USB-シリアル変換ユニット（センサーに付属してる）

### リポジトリのクローン

```base
git clone https://github.com/KokiLee/serial_async.git
```

### 仮想環境の作

```bash
python -m venv .venv
```

### 依存関係のインストール

```bash
pip install -e .
```

### 設定ファイルの編集

`config/config.ini`を編集してシリアルポート設定を調整

```ini
[serial_set]
portname = COM3
baudrate = 9600
timeout = 3
stopbits = 1
bytesize = 8
parity = N
xonxoff = True
readwait = 0.1
```

### アプリケーションの実行

```bash
pythono apps/serial_app.py
```

## 機能詳細

### 非同期シリアル通信

- AsyncSerialCommunicator: asyncio.Protcolを継承した非同期通信クラス
- SerialCommunication: データ送受信の管理
- AsyncSerialManager: シリアルポートの管理

### データ解析

- DataParser: バイトデータのチェックサム検証
- HWT905_TTL_Dataparser: センサーからのデータを解析するクラス

### 可視化

- AngularPlotter: 角度データのリアルタイムプロット
- DirectionPlotter: 磁場データの方向と強度の可視化
- CombinedPlotter: 角度と磁場データを同時に表示

### GUI

- MainWindow: PyQt5ベースのメインウインドウ
- グラフ表示
- 非同期イベント処理

## テスト

## 開発

### 開発環境

- Python 3.9.2
- code formatter: black
- requirements.txt

### プロジェクト構造

```
src/
├── serial_communication_async.py  # メイン通信モジュール
│   ├── AsyncSerialCommunicator   # 非同期通信プロトコル
│   ├── SerialCommunication       # データ送受信
│   ├── AngularPlotter           # 角度プロット
│   ├── DirectionPlotter         # 磁場プロット
│   ├── CombinedPlotter          # 複合プロット
│   ├── AsyncSerialManager       # シリアル管理
│   ├── DataProcessor            # データ処理
│   └── MainWindow              # GUIウィンドウ
├── constants.py                  # 定数定義
└── hwt905_ttl_dataparser.py     # HWT905パーサー
```

## ログ

アプリケーションのログは`logs/apps.log`に出力されます：

- シリアル通信の状態
- データ受信ログ
- エラー情報
- デバッグ情報

## 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。
