# fSpy Maya importer (Maya 2022-2025 PySide2/PySide6)
fSpy importer for Maya to import camera data created with fSpy
fSpyで作成したカメラデータをMayaにインポートするためのPythonスクリプト

# Features
- ✅ Import fSpy project files into Maya to import camera position, rotation, lens focal length, and image size
- ✅ Automatically import images and set up image planes
- ✅ Supports Maya 2022, 2023, 2024, 2025 (both PySide2 and PySide6)

# Requirements
- Maya 2022 or later (tested on Maya 2022, Maya 2025)
- PySide2 or PySide6
- [fSpy (https://fspy.io/)](https://fspy.io/)

## Installation
1. Download the `fspy_importer.py` file
2. Place the downloaded script in the scripts folder (`C:\Users\{UserName}\Documents\maya\{Version}\scripts`)

## Usage
1. Run the following code in the Maya script editor:
```python
import fspy_importer
fspy_importer.launch_importer()
```
2. Select an fSpy project file and click the `Import Camera` button
3. Specify the location of the image file (if canceled, the image plane will not be created)
4. Set the offset as needed

## Debug
You can enable trace and debug logs with options:
```python
import fspy_importer
fspy_importer.launch_importer(trace=True, debug=True) 
```

## License
[MIT Licence](LICENCE.md)


# 機能
- ✅ fSpyプロジェクトファイルをMaya上で読み込み、カメラの位置、回転、レンズの焦点距離、画像サイズをインポート
- ✅ 画像の自動インポート、イメージプレーンの自動設定
- ✅ Maya 2022, 2023, 2024, 2025に対応 (PySide2, PySide6の両方に対応)

# 環境
- Maya 2022以降 (Maya 2022, Maya2025で動作確認済み)
- PySide2またはPySide6
- [fSpy (https://fspy.io/)](https://fspy.io/)

## インストール方法
1. `fspy_importer.py`をダウンロード
2. ダウンロードしたスクリプトをscriptsフォルダ(`C:\Users\{UserName}\Documents\maya\{Version}\scripts`)に配置
(日本語版Mayaでは`C:\Users\{UserName}\Documents\maya\{Version}\ja_JP\scripts`に配置します)

## 使い方
1. Mayaのスクリプトエディタで以下のコードを実行:
```python
import fspy_importer
fspy_importer.launch_importer()
```
2. fSpyプロジェクトファイルを選択して`Import Camera`ボタンをクリック
3. 画像ファイルの保存先を指定 (キャンセルした場合、イメージプレーンは生成されません)
4. 必要に応じてオフセットを設定します

## デバック
オプションでトレースログとデバックログを有効にすることができます:
```python
import fspy_importer
fspy_importer.launch_importer(trace=True, debug=True) 
```

## ライセンス
[MIT Licence](LICENCE.md)
