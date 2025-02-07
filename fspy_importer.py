# プラグイン情報の定数
PLUGIN_NAME = "fSpyImporter"
PLUGIN_LABEL = "fSpy Importer"
PLUGIN_INITIAL_WIDTH = 500
PLUGIN_INITIAL_HEIGHT = 500

# デバッグ設定
DEBUG_LEVELS = {
    'trace': False,
    'debug': False,
    'info': True,
    'error': True
}

import maya.cmds as cmds
import struct
import os
import math

# numpy の条件付きインポート
try:
    import numpy as np
    USE_NUMPY = True
except ImportError:
    USE_NUMPY = False
    print('['+PLUGIN_NAME+'] Numpy not found, using fallback implementation.')

import json

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance



class Matrix3x3:
    """numpy が利用できない場合の3x3行列実装"""
    def __init__(self, data):
        self.data = [[data[i][j] for j in range(3)] for i in range(3)]
    
    def __getitem__(self, key):
        i, j = key
        return self.data[i][j]
    
    @staticmethod
    def dot_product(a, b):
        """ベクトルの内積"""
        return sum(x * y for x, y in zip(a, b))
    
    def dot(self, other):
        """行列の積"""
        result = [[0 for _ in range(3)] for _ in range(3)]
        for i in range(3):
            for j in range(3):
                row = [self.data[i][k] for k in range(3)]
                col = [other.data[k][j] for k in range(3)]
                result[i][j] = self.dot_product(row, col)
        return Matrix3x3(result)

def create_rotation_matrix(x, y, z):
    """回転行列の生成（numpy非依存版）"""
    # X回転行列
    rot_x = [
        [1, 0, 0],
        [0, math.cos(x), -math.sin(x)],
        [0, math.sin(x), math.cos(x)]
    ]
    
    # Y回転行列
    rot_y = [
        [math.cos(y), 0, math.sin(y)],
        [0, 1, 0],
        [-math.sin(y), 0, math.cos(y)]
    ]
    
    # Z回転行列
    rot_z = [
        [math.cos(z), -math.sin(z), 0],
        [math.sin(z), math.cos(z), 0],
        [0, 0, 1]
    ]
    
    if USE_NUMPY:
        return np.array(rot_z).dot(np.array(rot_y)).dot(np.array(rot_x))
    else:
        return Matrix3x3(rot_z).dot(Matrix3x3(rot_y)).dot(Matrix3x3(rot_x))

def rotation_matrix_to_euler(matrix):
    """回転行列をオイラー角に変換する"""
    if USE_NUMPY:
        # numpyが利用可能な場合
        sy = math.sqrt(matrix[0, 0] ** 2 + matrix[1, 0] ** 2)
        singular = sy < 1e-6
        if not singular:
            x = math.atan2(matrix[2, 1], matrix[2, 2])
            y = math.atan2(-matrix[2, 0], sy)
            z = math.atan2(matrix[1, 0], matrix[0, 0])
        else:
            x = math.atan2(-matrix[1, 2], matrix[1, 1])
            y = math.atan2(-matrix[2, 0], sy)
            z = 0
    else:
        # numpyが利用できない場合（Matrix3x3クラスを使用）
        matrix_data = matrix.data if hasattr(matrix, 'data') else matrix
        sy = math.sqrt(matrix_data[0][0] ** 2 + matrix_data[1][0] ** 2)
        singular = sy < 1e-6
        if not singular:
            x = math.atan2(matrix_data[2][1], matrix_data[2][2])
            y = math.atan2(-matrix_data[2][0], sy)
            z = math.atan2(matrix_data[1][0], matrix_data[0][0])
        else:
            x = math.atan2(-matrix_data[1][2], matrix_data[1][1])
            y = math.atan2(-matrix_data[2][0], sy)
            z = 0
    
    # 常にリストとして返す
    return [x, y, z]

class FSpyParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.state_data = None
        self.image_data = None
        self.image_path = None  # 保存された画像のパスを保持

    def parse(self):
        try:
            log_message("Opening fSpy file.", "trace")
            with open(self.filepath, 'rb') as f:
                # ヘッダーの検証
                file_id = f.read(4)
                log_message(f"File ID: {file_id}", "trace")
                if file_id != b'fspy':
                    raise ValueError("Invalid fSpy file format")

                # バージョンとサイズの読み込み
                version = struct.unpack('<I', f.read(4))[0]
                log_message(f"Version: {version}", "trace")
                state_size = struct.unpack('<I', f.read(4))[0]
                log_message(f"State size: {state_size}", "trace")
                image_size = struct.unpack('<I', f.read(4))[0]
                log_message(f"Image size: {image_size}", "trace")

                # JSONデータの読み込み
                state_data = f.read(state_size)
                log_message(f"Raw state data: {state_data[:100]}... (truncated)", "trace")
                # ヌル文字を削除してデコード
                state_data = state_data.replace(b'\x00', b'')
                self.state_data = json.loads(state_data.decode('utf-8'))
                log_message(f"Parsed JSON data: {self.state_data}", "trace")

                # 画像データの読み込み
                self.image_data = f.read(image_size)
                log_message("Image data loaded successfully.", "trace")

                log_message(f"Successfully parsed fSpy file: {self.filepath}", "info")
                return True
        except Exception as e:
            log_message(f"Failed to parse fSpy file: {str(e)}", "error")
            return False

    def save_image(self, default_filename=None):
        """画像データを保存し、保存されたパスを返す"""
        if not self.image_data:
            return None

        if default_filename is None:
            default_filename = os.path.splitext(os.path.basename(self.filepath))[0] + ".png"

        project_path = cmds.workspace(query=True, rootDirectory=True)
        default_dir = os.path.join(project_path, "images")

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, 
            "Save Image File",
            os.path.join(default_dir, default_filename),
            "Images (*.png)"
        )

        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(self.image_data)
                self.image_path = file_path
                log_message(f"Image saved to: {file_path}", "info")
                return file_path
            except Exception as e:
                log_message(f"Failed to save image: {str(e)}", "error")
                return None
        return None

    def get_camera_transform(self):
        """カメラのトランスフォーム行列を計算して返す"""
        try:
            camera_parameters = self.state_data.get('cameraParameters', {})
            if not camera_parameters:
                raise ValueError("No camera parameters found")

            transform = camera_parameters.get('cameraTransform', {})
            log_message(f"Camera transform data: {transform}", "trace")
            rows = transform.get('rows', [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
            
            # 位置の取得
            position = [rows[0][3], rows[1][3], rows[2][3]]
            
            # 回転行列の取得（3x3部分）
            rotation_matrix = [[rows[i][j] for j in range(3)] for i in range(3)]
            
            if USE_NUMPY:
                rotation_matrix = np.array(rotation_matrix)
            else:
                rotation_matrix = Matrix3x3(rotation_matrix)
                
            log_message(f"Position: {position}, Rotation matrix: {rotation_matrix}", "trace")
            return position, rotation_matrix
            
        except Exception as e:
            log_message(f"Failed to calculate camera transform: {str(e)}", "error")
            return None


class PluginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(PluginDialog, self).__init__(parent)
        self.setWindowTitle(PLUGIN_LABEL)
        self.fspy_parser = None
        self.group = None
        self.camera = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # ファイル選択部分
        file_layout = QtWidgets.QHBoxLayout()
        self.file_path = QtWidgets.QLineEdit()
        browse_button = QtWidgets.QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(browse_button)

        # カメラ情報表示用テキストフィールドを追加
        info_group = QtWidgets.QGroupBox("Camera Information")
        info_layout = QtWidgets.QVBoxLayout()
        self.info_text = QtWidgets.QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(100)
        info_layout.addWidget(self.info_text)
        info_group.setLayout(info_layout)

        # オフセット値入力 (X, Y, Z それぞれDoubleSpinBoxで入力)
        offset_group_box = QtWidgets.QGroupBox("Offsets")
        offset_layout = QtWidgets.QHBoxLayout()

        # アップ軸ウィジェット
        self.up_axis = QtWidgets.QComboBox()
        self.up_axis.addItems(["X", "Y", "Z", "-X", "-Y", "-Z"])
        self.up_axis.setEnabled(False)  # 初期状態では無効
        self.up_axis.currentIndexChanged.connect(self.apply_up_axis)
        offset_layout.addWidget(QtWidgets.QLabel("Up Axis:"))
        offset_layout.addWidget(self.up_axis)

        self.offset_x = QtWidgets.QDoubleSpinBox()
        self.offset_x.setRange(-360, 360)
        self.offset_x.setEnabled(False)  # 初期状態では無効
        self.offset_x.valueChanged.connect(self.apply_up_axis)
        offset_layout.addWidget(QtWidgets.QLabel("Offset X:"))
        offset_layout.addWidget(self.offset_x)
        # -/+ボタン (90度ずつオフセット値を変更)
        self.offset_x_minus = QtWidgets.QPushButton("-")
        self.offset_x_minus.setEnabled(False)
        self.offset_x_minus.setMaximumWidth(20)
        self.offset_x_minus.clicked.connect(lambda: self.offset_x.setValue(self.offset_x.value() - 90))
        offset_layout.addWidget(self.offset_x_minus)
        self.offset_x_plus = QtWidgets.QPushButton("+")
        self.offset_x_plus.setEnabled(False)
        self.offset_x_plus.setMaximumWidth(20)
        self.offset_x_plus.clicked.connect(lambda: self.offset_x.setValue(self.offset_x.value() + 90))
        offset_layout.addWidget(self.offset_x_plus)

        self.offset_y = QtWidgets.QDoubleSpinBox()
        self.offset_y.setRange(-360, 360)
        self.offset_y.setEnabled(False)  # 初期状態では無効
        self.offset_y.valueChanged.connect(self.apply_up_axis)
        offset_layout.addWidget(QtWidgets.QLabel("Offset Y:"))
        offset_layout.addWidget(self.offset_y)
        # -/+ボタン (90度ずつオフセット値を変更)
        self.offset_y_minus = QtWidgets.QPushButton("-")
        self.offset_y_minus.setEnabled(False)
        self.offset_y_minus.setMaximumWidth(20)
        self.offset_y_minus.clicked.connect(lambda: self.offset_y.setValue(self.offset_y.value() - 90))
        offset_layout.addWidget(self.offset_y_minus)
        self.offset_y_plus = QtWidgets.QPushButton("+")
        self.offset_y_plus.setEnabled(False)
        self.offset_y_plus.setMaximumWidth(20)
        self.offset_y_plus.clicked.connect(lambda: self.offset_y.setValue(self.offset_y.value() + 90))
        offset_layout.addWidget(self.offset_y_plus)

        self.offset_z = QtWidgets.QDoubleSpinBox()
        self.offset_z.setRange(-360, 360)
        self.offset_z.setEnabled(False)  # 初期状態では無効
        self.offset_z.valueChanged.connect(self.apply_up_axis)
        offset_layout.addWidget(QtWidgets.QLabel("Offset Z:"))
        offset_layout.addWidget(self.offset_z)
        # -/+ボタン (90度ずつオフセット値を変更)
        self.offset_z_minus = QtWidgets.QPushButton("-")
        self.offset_z_minus.setEnabled(False)
        self.offset_z_minus.setMaximumWidth(20)
        self.offset_z_minus.clicked.connect(lambda: self.offset_z.setValue(self.offset_z.value() - 90))
        offset_layout.addWidget(self.offset_z_minus)
        self.offset_z_plus = QtWidgets.QPushButton("+")
        self.offset_z_plus.setEnabled(False)
        self.offset_z_plus.setMaximumWidth(20)
        self.offset_z_plus.clicked.connect(lambda: self.offset_z.setValue(self.offset_z.value() + 90))
        offset_layout.addWidget(self.offset_z_plus)

        offset_group_box.setLayout(offset_layout)

        # インポートボタン
        import_button = QtWidgets.QPushButton("Import Camera")
        import_button.clicked.connect(self.import_camera)

        layout.addLayout(file_layout)
        layout.addWidget(info_group)
        layout.addWidget(offset_group_box)
        layout.addWidget(import_button)

    def browse_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select fSpy file", "", "fSpy Files (*.fspy)")
        if file_path:
            self.file_path.setText(file_path)
            self.fspy_parser = FSpyParser(file_path)
            if self.fspy_parser.parse():
                log_message("File loaded successfully", "info")
                # ファイル読み込み時にカメラ情報を表示
                params = self.fspy_parser.state_data.get('cameraParameters', {})
                transform_data = self.fspy_parser.get_camera_transform()
                if params:
                    self.update_camera_info(params, transform_data)
                    log_message("Updated camera information display", "info")

    def update_camera_info(self, params, transform_data=None):
        """カメラ情報をテキストフィールドに表示"""
        try:
            info_text = []
            
            # ファイル名
            info_text.append(f"File: {os.path.basename(self.fspy_parser.filepath)}")
            
            # 画像サイズ
            image_width = float(params.get('imageWidth', 1920))
            image_height = float(params.get('imageHeight', 1920))
            info_text.append(f"Image Size: {int(image_width)}x{int(image_height)}")
            info_text.append(f"Aspect Ratio: {image_width/image_height:.3f}")
            
            # FOV
            horizontal_fov = params.get('horizontalFieldOfView')
            if horizontal_fov is not None:
                fov_degrees = math.degrees(float(horizontal_fov))
                info_text.append(f"Horizontal FOV: {fov_degrees:.2f}°")
            
            # カメラ位置
            if transform_data:
                pos, rot_matrix = transform_data
                info_text.append("Camera Position:")
                info_text.append(f"  X: {pos[0]:.3f}")
                info_text.append(f"  Y: {pos[1]:.3f}")
                info_text.append(f"  Z: {pos[2]:.3f}")

                # 回転情報を追加
                rot_euler = rotation_matrix_to_euler(rot_matrix)
                info_text.append("Camera Rotation (degrees):")
                info_text.append(f"  X: {math.degrees(rot_euler[0]):.3f}")
                info_text.append(f"  Y: {math.degrees(rot_euler[1]):.3f}")
                info_text.append(f"  Z: {math.degrees(rot_euler[2]):.3f}")
            
            # Focal Length
            focal_length = 35.0  # デフォルト値
            if horizontal_fov is not None:
                horiz_aperture_mm = 36.0
                focal_length = (horiz_aperture_mm / 2) / math.tan(horizontal_fov / 2)
            info_text.append(f"Focal Length: {focal_length:.2f}mm")
            
            # Principal Point
            principal_point = params.get('principalPoint', {'x': 0, 'y': 0})
            if isinstance(principal_point, dict):
                info_text.append("Principal Point:")
                info_text.append(f"  X: {principal_point.get('x', 0):.3f}")
                info_text.append(f"  Y: {principal_point.get('y', 0):.3f}")
            
            # 単位情報
            unit = self.fspy_parser.state_data.get('calibrationSettingsBase', {}).get('referenceDistanceUnit', 'Meters')
            info_text.append(f"Unit: {unit}")

            # テキストを設定
            self.info_text.setText("\n".join(info_text))
            log_message("Camera information updated successfully", "info")
            
        except Exception as e:
            log_message(f"Error updating camera information: {str(e)}", "error")
            import traceback
            log_message(f"Traceback: {traceback.format_exc()}", "error")

    def enable_offset_controls(self):
        """オフセットコントロールを有効化"""
        controls = [
            self.up_axis,
            self.offset_x, self.offset_x_minus, self.offset_x_plus,
            self.offset_y, self.offset_y_minus, self.offset_y_plus,
            self.offset_z, self.offset_z_minus, self.offset_z_plus
        ]
        for control in controls:
            control.setEnabled(True)
        log_message("Offset controls enabled", "info")

    def get_relative_path(self, filepath):
        """Mayaプロジェクトからの相対パスを取得"""
        try:
            project_path = cmds.workspace(query=True, rootDirectory=True)
            project_path = os.path.normpath(project_path)
            filepath = os.path.normpath(filepath)
            
            # プロジェクトパス内かチェック
            if filepath.startswith(project_path):
                rel_path = os.path.relpath(filepath, project_path)
                log_message(f"Converted to relative path: {rel_path}", "info")
                return rel_path
            return filepath
        except Exception as e:
            log_message(f"Failed to get relative path: {str(e)}", "error")
            return filepath

    def import_camera(self):
        if not self.fspy_parser or not self.fspy_parser.state_data:
            log_message("No valid fSpy file loaded", "error")
            return

        try:
            # 先に画像を保存
            if self.fspy_parser.image_data:
                default_filename = os.path.splitext(os.path.basename(self.fspy_parser.filepath))[0] + ".jpg"
                image_path = self.fspy_parser.save_image(default_filename)
                if not image_path:
                    if not QtWidgets.QMessageBox.question(
                        self,
                        "Continue Without Image",
                        "No image was saved. Do you want to continue without the image plane?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    ) == QtWidgets.QMessageBox.Yes:
                        return

            # カメラをグループの中に入れて生成
            self.group = cmds.group(empty=True, name="fspy_camera_group")
            self.camera = cmds.camera(name="fspy_camera")[0]
            camera_shape = cmds.listRelatives(self.camera, shapes=True)[0]
            cmds.parent(self.camera, self.group)
            
            params = self.fspy_parser.state_data.get('cameraParameters', {})
            transform_data = self.fspy_parser.get_camera_transform()

            # カメラ情報の表示を更新
            if params:
                self.update_camera_info(params, transform_data)

            # 位置を設定
            if transform_data:
                pos, rot_matrix = transform_data

                cmds.setAttr(f"{self.camera}.translateX", pos[0])
                cmds.setAttr(f"{self.camera}.translateY", pos[1])
                cmds.setAttr(f"{self.camera}.translateZ", pos[2])
                log_message(f"Set position: {pos}", "info")

                # 回転を設定
                rot_euler = rotation_matrix_to_euler(rot_matrix)
                cmds.setAttr(f"{self.camera}.rotateX", math.degrees(rot_euler[0]))
                cmds.setAttr(f"{self.camera}.rotateY", math.degrees(rot_euler[1]))
                cmds.setAttr(f"{self.camera}.rotateZ", math.degrees(rot_euler[2]))
                log_message(f"Set rotation: {rot_euler}", "info")

            # カメラプロパティの設定
            if params:
                # フィルムバックの設定（mmからinchへの変換）
                image_width = float(params.get('imageWidth', 1920))
                image_height = float(params.get('imageHeight', 1080))
                aspect_ratio = image_width / image_height
                horiz_aperture_mm = 36.0  # 35mmフィルム規格
                vert_aperture_mm = horiz_aperture_mm / aspect_ratio
                mm_to_inch = 0.0393701
                horiz_aperture_inch = horiz_aperture_mm * mm_to_inch
                vert_aperture_inch = vert_aperture_mm * mm_to_inch

                cmds.setAttr(f"{camera_shape}.horizontalFilmAperture", horiz_aperture_inch)
                cmds.setAttr(f"{camera_shape}.verticalFilmAperture", vert_aperture_inch)
                log_message(f"Set film back (in inches): {horiz_aperture_inch}x{vert_aperture_inch}", "info")

                # フィルムオフセットの設定（mmからinchへの変換）
                principal_point = params.get('principalPoint', [0, 0])
                if isinstance(principal_point, list) and len(principal_point) == 2:
                    x_offset_mm = float(principal_point[0]) * horiz_aperture_mm
                    y_offset_mm = float(principal_point[1]) * vert_aperture_mm
                    x_offset_inch = x_offset_mm * mm_to_inch
                    y_offset_inch = y_offset_mm * mm_to_inch

                    cmds.setAttr(f"{camera_shape}.horizontalFilmOffset", x_offset_inch)
                    cmds.setAttr(f"{camera_shape}.verticalFilmOffset", y_offset_inch)
                    log_message(f"Set film offset (in inches): {x_offset_inch}x{y_offset_inch}", "info")

                # フィルムフィット調整
                cmds.setAttr(f"{camera_shape}.filmFit", 1)  # Horizontal fit

                # カメラをロックする
                cmds.setAttr(f"{self.camera}.tx", lock=True)

                # horizontalFieldOfViewの設定
                horizontal_fov = params.get('horizontalFieldOfView', None)
                if horizontal_fov is not None:
                    horizontal_fov_degrees = math.degrees(horizontal_fov)  # ラジアンから度に変換
                    focal_length = (horiz_aperture_mm / 2) / math.tan(math.radians(horizontal_fov_degrees) / 2)
                    cmds.setAttr(f"{camera_shape}.focalLength", focal_length)
                    log_message(f"Set focal length based on horizontalFieldOfView: {focal_length}", "info")

            # イメージプレーンの処理
            if image_path:
                # プロジェクトパスからの相対パスを取得
                image_path_for_plane = self.get_relative_path(image_path)
                # イメージプレーンの作成
                image_plane = cmds.imagePlane(camera=self.camera, fileName=image_path_for_plane)
                log_message(f"Image plane created with file: {image_path_for_plane}", "info")

            # オフセットコントロールを有効化
            self.enable_offset_controls()
            log_message("Camera created and controls enabled", "info")

        except Exception as e:
            log_message(f"Failed to create camera: {str(e)}", "error")
            raise

    def apply_up_axis(self):
        if not self.group:
            return

        up_axis = self.up_axis.currentText()
        offset_value = 90

        offset_x = self.offset_x.value()
        offset_y = self.offset_y.value()
        offset_z = self.offset_z.value()

        if up_axis == "X":
            cmds.setAttr(f"{self.group}.rotateX", offset_value + offset_x)
            cmds.setAttr(f"{self.group}.rotateY", offset_y)
            cmds.setAttr(f"{self.group}.rotateZ", offset_z)
        elif up_axis == "Y":
            cmds.setAttr(f"{self.group}.rotateX", offset_x)
            cmds.setAttr(f"{self.group}.rotateY", offset_value + offset_y)
            cmds.setAttr(f"{self.group}.rotateZ", offset_z)
        elif up_axis == "Z":
            cmds.setAttr(f"{self.group}.rotateX", offset_x)
            cmds.setAttr(f"{self.group}.rotateY", offset_y)
            cmds.setAttr(f"{self.group}.rotateZ", offset_value + offset_z)
        elif up_axis == "-X":
            cmds.setAttr(f"{self.group}.rotateX", -offset_value + offset_x)
            cmds.setAttr(f"{self.group}.rotateY", offset_y)
            cmds.setAttr(f"{self.group}.rotateZ", offset_z)
        elif up_axis == "-Y":
            cmds.setAttr(f"{self.group}.rotateX", offset_x)
            cmds.setAttr(f"{self.group}.rotateY", -offset_value + offset_y)
            cmds.setAttr(f"{self.group}.rotateZ", offset_z)
        elif up_axis == "-Z":
            cmds.setAttr(f"{self.group}.rotateX", offset_x)
            cmds.setAttr(f"{self.group}.rotateY", offset_y)
            cmds.setAttr(f"{self.group}.rotateZ", -offset_value + offset_z)


        log_message(f"Set up axis: {up_axis}, offset value: {offset_value}", "info")


def create_plugin_dialog():
    global dialog
    dialog = PluginDialog()
    dialog.resize(PLUGIN_INITIAL_WIDTH, PLUGIN_INITIAL_HEIGHT)
    dialog.show()


def set_debug_level(trace=False, debug_flag=False):
    """デバッグレベルを設定"""
    global DEBUG_LEVELS
    DEBUG_LEVELS['trace'] = trace
    DEBUG_LEVELS['debug'] = debug_flag
    log_message(f"Debug levels set - trace: {trace}, debug: {debug_flag}", "info")

def log_message(message, level):
    """デバッグ情報を出力"""
    if DEBUG_LEVELS.get(level, True):  # 未定義のレベルはデフォルトで表示
        print(f'[{PLUGIN_NAME}] [{level.upper()}]: {message}')

def launch_importer(trace=False, debug=False):
    """シェルフからの呼び出し用関数"""
    set_debug_level(trace, debug)
    create_plugin_dialog()

# シェルフボタンからの使用例:
# import fspy_importer
# fspy_importer.launch_importer(trace=True, debug=True)  # すべてのログを表示
# または
# fspy_importer.launch_importer()  # info と error のみ表示