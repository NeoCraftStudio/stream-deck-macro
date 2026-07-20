import os
import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QComboBox, QLineEdit, QDialogButtonBox, QLabel, QMessageBox, QSpinBox,
    QKeySequenceEdit, QFileDialog
)

CONFIG_PATH = "config.json"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)


def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


class ConfigDialog(QDialog):
    def __init__(self, btn_idx):
        super().__init__()
        self.setWindowTitle(f"Configure BTN{btn_idx}")

        self.layer_box = QComboBox()
        self.layer_box.addItems(["layer1", "layer2"])

        self.type_box = QComboBox()
        self.type_box.addItems(["keyboard", "macro", "obs_scene", "sound", "empty"])
        self.type_box.currentTextChanged.connect(self.on_type_changed)

        self.value_edit = QLineEdit()
        self.macro_edit = QKeySequenceEdit()
        self.macro_edit.hide()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Layer:"))
        layout.addWidget(self.layer_box)
        layout.addWidget(QLabel("Action type:"))
        layout.addWidget(self.type_box)
        layout.addWidget(QLabel("Value:"))
        layout.addWidget(self.value_edit)
        layout.addWidget(self.macro_edit)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def on_type_changed(self, text):
        is_macro = (text == "macro")
        self.macro_edit.setVisible(is_macro)
        self.value_edit.setVisible(not is_macro)

    def get_value(self):
        if self.type_box.currentText() == "macro":
            return self.macro_edit.keySequence().toString().lower()
        return self.value_edit.text()


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(config["settings"]["2fx_timeout_seconds"])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Tempo de espera da segunda função (segundos):"))
        layout.addWidget(self.timeout_spin)
        layout.addWidget(buttons)
        self.setLayout(layout)


class EncodersDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configure Encoders")

        self.mode_boxes = {}
        self.exe_edits = {}
        self.browse_buttons = {}

        layout = QVBoxLayout()
        encoders = config.get("encoders", {})

        for enc_id in ["1", "2", "3"]:
            target = encoders.get(enc_id, {}).get("target", "system")
            is_app = target.startswith("app:")

            mode_box = QComboBox()
            mode_box.addItems(["Volume Geral", "Aplicativo"])
            mode_box.setCurrentIndex(1 if is_app else 0)

            exe_edit = QLineEdit()
            exe_edit.setReadOnly(True)
            if is_app:
                exe_edit.setText(target.split("app:", 1)[1])

            browse_button = QPushButton("Selecionar...")
            browse_button.clicked.connect(lambda checked=False, e=enc_id: self.browse_for_exe(e))

            exe_edit.setEnabled(is_app)
            browse_button.setEnabled(is_app)

            mode_box.currentTextChanged.connect(
                lambda text, e=enc_id: self.on_mode_changed(e, text)
            )

            self.mode_boxes[enc_id] = mode_box
            self.exe_edits[enc_id] = exe_edit
            self.browse_buttons[enc_id] = browse_button

            row = QHBoxLayout()
            row.addWidget(mode_box)
            row.addWidget(exe_edit)
            row.addWidget(browse_button)

            layout.addWidget(QLabel(f"Encoder {enc_id}"))
            layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def on_mode_changed(self, enc_id, text):
        is_app = (text == "Aplicativo")
        self.exe_edits[enc_id].setEnabled(is_app)
        self.browse_buttons[enc_id].setEnabled(is_app)

    def browse_for_exe(self, enc_id):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar aplicativo", "", "Executáveis (*.exe)")
        if path:
            self.exe_edits[enc_id].setText(os.path.basename(path))

    def get_target(self, enc_id):
        if self.mode_boxes[enc_id].currentText() == "Aplicativo":
            return f"app:{self.exe_edits[enc_id].text()}"
        return "system"


def on_button_clicked(idx):
    if idx == 15:
        QMessageBox.information(None, "2FX", "The 2FX key has no configurable action — it's the layer toggle.")
        return

    dialog = ConfigDialog(idx)
    if dialog.exec():
        layer = dialog.layer_box.currentText()
        action_type = dialog.type_box.currentText()
        value = dialog.get_value()

        btn_key = str(idx)
        if btn_key not in config["buttons"]:
            config["buttons"][btn_key] = {
                "layer1": {"type": "empty"},
                "layer2": {"type": "empty"},
            }
        config["buttons"][btn_key][layer] = {"type": action_type, "value": value}
        save_config()
        print(f"Saved BTN{idx} [{layer}] = type={action_type}, value={value}")
    else:
        print(f"BTN{idx} config cancelled")


def on_settings_clicked():
    dialog = SettingsDialog()
    if dialog.exec():
        config["settings"]["2fx_timeout_seconds"] = dialog.timeout_spin.value()
        save_config()
        print("Settings saved")
    else:
        print("Settings cancelled")


def on_encoders_clicked():
    dialog = EncodersDialog()
    if dialog.exec():
        if "encoders" not in config:
            config["encoders"] = {}
        for enc_id in ["1", "2", "3"]:
            config["encoders"][enc_id] = {"target": dialog.get_target(enc_id)}
        save_config()
        print("Encoders saved")
    else:
        print("Encoders cancelled")


app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle("Stream Deck Macro")
window.resize(400, 500)

central = QWidget()
outer_layout = QVBoxLayout()

grid = QGridLayout()
for row in range(4):
    for col in range(4):
        idx = row * 4 + col
        label = "2FX" if idx == 15 else f"BTN{idx}"
        button = QPushButton(label)
        button.setMinimumSize(80, 80)
        button.clicked.connect(lambda checked=False, i=idx: on_button_clicked(i))
        grid.addWidget(button, row, col)

settings_button = QPushButton("Settings")
settings_button.clicked.connect(on_settings_clicked)

encoders_button = QPushButton("Configure Encoders")
encoders_button.clicked.connect(on_encoders_clicked)

outer_layout.addLayout(grid)
outer_layout.addWidget(settings_button)
outer_layout.addWidget(encoders_button)
central.setLayout(outer_layout)
window.setCentralWidget(central)

window.show()
sys.exit(app.exec())