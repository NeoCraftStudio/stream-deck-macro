import os
import sys
import time
import json
import math
import colorsys
import serial
import sounddevice as sd
import soundfile as sf
import pyautogui
import obsws_python as obs
from pycaw.pycaw import AudioUtilities
from PySide6.QtCore import QTimer, Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QImage, QPen, QIcon, QPixmap, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QComboBox, QLineEdit, QDialogButtonBox, QLabel, QSpinBox,
    QKeySequenceEdit, QFileDialog, QSlider, QSystemTrayIcon, QMenu
)

CONFIG_PATH = "config.json"
PORT = "COM5"
BAUD = 9600
VOLUME_STEP = 0.05

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

config["settings"].setdefault("led_brightness", 50)
config["settings"].setdefault("led_speed_percent", 50)
config["settings"].setdefault("led_pattern", "rainbow_wave")
config["settings"].setdefault("led_color", [255, 0, 0])


def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def percent_to_ms(percent):
    return round(60 - (percent / 100) * 55)


def led_cycle_increment():
    # Matches the firmware's real timing: a full hue rotation takes
    # 256 steps (65536 hue range / 256 per step) of animSpeedMs each.
    # The app polls every 50ms, so this keeps the two in sync.
    ms_value = percent_to_ms(config["settings"]["led_speed_percent"])
    poll_interval_ms = 50
    return poll_interval_ms / (256 * ms_value)


# ---- 2FX state machine ----
class TwoFXState:
    def __init__(self, timeout_seconds):
        self.armed = False
        self.armed_at = None
        self.timeout_seconds = timeout_seconds

    def arm(self):
        self.armed = True
        self.armed_at = time.time()
        print("2FX armed")

    def disarm(self):
        self.armed = False
        self.armed_at = None
        print("2FX disarmed")

    def check_timeout(self):
        if self.armed and (time.time() - self.armed_at) > self.timeout_seconds:
            self.disarm()
            print("2FX timed out")

    def handle_button(self, btn_id):
        if btn_id == 15:
            if self.armed:
                self.disarm()
            else:
                self.arm()
            return None
        layer = "layer2" if self.armed else "layer1"
        if self.armed:
            self.disarm()
        return layer


two_fx_state = TwoFXState(config["settings"]["2fx_timeout_seconds"])


# ---- OBS connection (optional — app still works if OBS isn't running) ----
obs_client = None
try:
    with open("tests/obs_secrets.json", "r") as f:
        obs_secrets = json.load(f)
    obs_client = obs.ReqClient(host=obs_secrets["host"], port=obs_secrets["port"], password=obs_secrets["password"])
    print("Connected to OBS")
except Exception as e:
    print(f"OBS not connected: {e}")


# ---- Action execution ----
def execute_action(action):
    action_type = action.get("type")
    value = action.get("value")

    if action_type in ("keyboard", "macro"):
        keys = value.split("+")
        pyautogui.hotkey(*keys)
        print(f"Executed {action_type}: {value}")

    elif action_type == "sound":
        try:
            data, samplerate = sf.read(value)
            sd.play(data, samplerate)
            print(f"Playing sound: {value}")
        except Exception as e:
            print(f"Sound playback failed: {e}")

    elif action_type == "obs_scene":
        if obs_client:
            obs_client.set_current_program_scene(value)
            print(f"Switched OBS scene: {value}")
        else:
            print("OBS not connected, can't switch scene")

    elif action_type == "empty":
        pass

    else:
        print(f"Action type '{action_type}' not implemented yet")


# ---- Volume control ----
def get_system_volume_interface():
    return AudioUtilities.GetSpeakers().EndpointVolume


def adjust_system_volume(delta):
    vol = get_system_volume_interface()
    current = vol.GetMasterVolumeLevelScalar()
    new = max(0.0, min(1.0, current + delta))
    vol.SetMasterVolumeLevelScalar(new, None)
    print(f"System volume: {int(new * 100)}%")


def toggle_system_mute():
    vol = get_system_volume_interface()
    muted = vol.GetMute()
    vol.SetMute(0 if muted else 1, None)
    print(f"System {'unmuted' if muted else 'muted'}")


def get_app_session(process_name):
    for session in AudioUtilities.GetAllSessions():
        if session.Process and session.Process.name().lower() == process_name.lower():
            return session
    return None


def adjust_app_volume(process_name, delta):
    session = get_app_session(process_name)
    if not session:
        print(f"{process_name} not found among audio sessions")
        return
    vol = session.SimpleAudioVolume
    new = max(0.0, min(1.0, vol.GetMasterVolume() + delta))
    vol.SetMasterVolume(new, None)
    print(f"{process_name} volume: {int(new * 100)}%")


def toggle_app_mute(process_name):
    session = get_app_session(process_name)
    if not session:
        print(f"{process_name} not found among audio sessions")
        return
    vol = session.SimpleAudioVolume
    muted = vol.GetMute()
    vol.SetMute(0 if muted else 1, None)
    print(f"{process_name} {'unmuted' if muted else 'muted'}")


def handle_encoder_event(enc_id, event):
    target = config.get("encoders", {}).get(enc_id, {}).get("target", "system")
    is_app = target.startswith("app:")
    process_name = target.split("app:", 1)[1] if is_app else None

    if event in ("CW", "CCW"):
        delta = VOLUME_STEP if event == "CW" else -VOLUME_STEP
        if is_app:
            adjust_app_volume(process_name, delta)
        else:
            adjust_system_volume(delta)
    elif event == "PUSH":
        if is_app:
            toggle_app_mute(process_name)
        else:
            toggle_system_mute()


# ---- GUI visual state ----
button_widgets = {}
button_pressed = {i: False for i in range(16)}
current_led_mode = config["settings"]["led_pattern"]


def update_button_style(idx):
    parts = []
    if button_pressed.get(idx):
        parts.append("background-color: gray;")
    if two_fx_state.armed and idx != 15:
        parts.append("border: 3px solid red;")
    button_widgets[idx].setStyleSheet(" ".join(parts))


def update_all_button_styles():
    for idx in button_widgets:
        update_button_style(idx)


def send_led_command(cmd):
    ser.write((cmd + "\n").encode())


def apply_idle_led_pattern():
    global current_led_mode
    pattern = config["settings"]["led_pattern"]
    r, g, b = config["settings"]["led_color"]
    current_led_mode = pattern
    if pattern == "solid":
        send_led_command(f"LED:MODE:SOLID:{r},{g},{b}")
    elif pattern == "breathing":
        send_led_command(f"LED:MODE:BREATHE:{r},{g},{b}")
    elif pattern == "color_cycle":
        send_led_command("LED:MODE:COLORCYCLE")
    else:
        send_led_command("LED:MODE:RAINBOWWAVE")


def set_2fx_override(armed):
    if armed:
        send_led_command("LED:MODE:BREATHE:255,0,0")
    else:
        apply_idle_led_pattern()


# ---- Animated border widget ----
class AnimatedBorder(QWidget):
    def __init__(self):
        super().__init__()
        self.hue_offset = 0.0
        self.mode = "rainbow"
        self.solid_color = QColor(255, 0, 0)
        self.inner_layout = QVBoxLayout()
        self.inner_layout.setContentsMargins(14, 14, 14, 14)
        self.setLayout(self.inner_layout)

    def set_solid(self, color):
        self.mode = "solid"
        self.solid_color = color
        self.update()

    def advance_rainbow(self, increment):
        self.mode = "rainbow"
        self.hue_offset = (self.hue_offset + increment) % 1.0
        self.update()

    def advance_color_cycle(self, increment):
        self.mode = "color_cycle"
        self.hue_offset = (self.hue_offset + increment) % 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        points = self._perimeter_points(rect, 150)
        total = len(points)
        pen = QPen()
        pen.setWidth(6)
        pen.setCapStyle(Qt.RoundCap)

        if self.mode == "color_cycle":
            r, g, b = colorsys.hsv_to_rgb(self.hue_offset, 1.0, 1.0)
            cycle_color = QColor(int(r * 255), int(g * 255), int(b * 255))

        for i in range(total):
            if self.mode == "rainbow":
                frac = i / total
                hue = (frac + self.hue_offset) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                color = QColor(int(r * 255), int(g * 255), int(b * 255))
            elif self.mode == "color_cycle":
                color = cycle_color
            else:
                color = self.solid_color
            pen.setColor(color)
            painter.setPen(pen)
            p1 = points[i]
            p2 = points[(i + 1) % total]
            painter.drawLine(p1, p2)

    def _perimeter_points(self, rect, n):
        w, h = rect.width(), rect.height()
        perim = 2 * (w + h)
        points = []
        for i in range(n):
            d = perim * i / n
            if d < w:
                x, y = rect.left() + d, rect.top()
            elif d < w + h:
                x, y = rect.right(), rect.top() + (d - w)
            elif d < 2 * w + h:
                x, y = rect.right() - (d - w - h), rect.bottom()
            else:
                x, y = rect.left(), rect.bottom() - (d - 2 * w - h)
            points.append(QPointF(x, y))
        return points


def update_border_animation():
    if two_fx_state.armed:
        phase = abs((time.time() * 2) % 2 - 1)
        intensity = int(100 + phase * 155)
        border_widget.set_solid(QColor(intensity, 0, 0))
    elif current_led_mode == "solid":
        r, g, b = config["settings"]["led_color"]
        border_widget.set_solid(QColor(r, g, b))
    elif current_led_mode == "breathing":
        phase = abs((time.time() * 2) % 2 - 1)
        scale = 0.4 + phase * 0.6
        r, g, b = config["settings"]["led_color"]
        border_widget.set_solid(QColor(int(r * scale), int(g * scale), int(b * scale)))
    elif current_led_mode == "color_cycle":
        border_widget.advance_color_cycle(led_cycle_increment())
    else:
        border_widget.advance_rainbow(led_cycle_increment())


# ---- Color wheel widget ----
class ColorWheel(QWidget):
    colorChanged = Signal(int, int, int)

    def __init__(self):
        super().__init__()
        self.setFixedSize(120, 120)
        self._wheel_enabled = True
        self._color = QColor(255, 0, 0)
        self._radius = self.width() / 2 - 4
        self._wheel_image = self._build_wheel_image()

    def _build_wheel_image(self):
        size = self.width()
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        cx, cy = size / 2, size / 2
        for y in range(size):
            for x in range(size):
                dx = x - cx
                dy = y - cy
                dist = math.hypot(dx, dy)
                if dist <= self._radius:
                    hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
                    sat = min(dist / self._radius, 1.0)
                    image.setPixelColor(x, y, QColor.fromHsvF(hue, sat, 1.0))
        return image

    def set_wheel_enabled(self, enabled):
        self._wheel_enabled = enabled
        self.update()

    def set_color(self, r, g, b):
        self._color = QColor(r, g, b)
        self.update()

    def get_color(self):
        return (self._color.red(), self._color.green(), self._color.blue())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()

        if self._wheel_enabled:
            painter.drawImage(0, 0, self._wheel_image)

            hue = self._color.hueF()
            sat = self._color.saturationF()
            if hue < 0:
                hue = 0
            angle = hue * 2 * math.pi
            dist = sat * self._radius
            marker_x = center.x() + dist * math.cos(angle)
            marker_y = center.y() + dist * math.sin(angle)

            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(self._color)
            painter.drawEllipse(int(marker_x) - 6, int(marker_y) - 6, 12, 12)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(100, 100, 100))
            painter.drawEllipse(center, self._radius, self._radius)

    def mousePressEvent(self, event):
        self.pick_color(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.pick_color(event.position())

    def pick_color(self, pos):
        if not self._wheel_enabled:
            return
        center = self.rect().center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        dist = min(math.hypot(dx, dy), self._radius)
        hue = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
        sat = dist / self._radius
        color = QColor.fromHsvF(hue, sat, 1.0)
        self._color = color
        self.update()
        self.colorChanged.emit(color.red(), color.green(), color.blue())


# ---- Serial handling ----
ser = serial.Serial(PORT, BAUD, timeout=0)
time.sleep(2)  # let the Arduino finish resetting after the serial connection opens
serial_buffer = ""

send_led_command(f"LED:BRIGHTNESS:{config['settings']['led_brightness']}")
send_led_command(f"LED:SPEED:{percent_to_ms(config['settings']['led_speed_percent'])}")
apply_idle_led_pattern()


def handle_serial_line(line):
    if line.startswith("BTN:"):
        parts = line.split(":")
        btn_id = int(parts[1])
        state = parts[2]

        if state == "DOWN":
            button_pressed[btn_id] = True
            was_armed = two_fx_state.armed
            layer = two_fx_state.handle_button(btn_id)
            if layer is not None:
                btn_key = str(btn_id)
                if btn_key in config["buttons"]:
                    execute_action(config["buttons"][btn_key][layer])
            if two_fx_state.armed != was_armed:
                set_2fx_override(two_fx_state.armed)
            update_all_button_styles()

        elif state == "UP":
            button_pressed[btn_id] = False
            update_button_style(btn_id)

    elif line.startswith("ENC:"):
        parts = line.split(":")
        enc_id = parts[1]
        event = parts[2]
        handle_encoder_event(enc_id, event)


def poll_serial():
    global serial_buffer
    was_armed = two_fx_state.armed
    two_fx_state.check_timeout()
    if two_fx_state.armed != was_armed:
        set_2fx_override(two_fx_state.armed)
        update_all_button_styles()

    if ser.in_waiting:
        data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
        serial_buffer += data
        while "\n" in serial_buffer:
            line, serial_buffer = serial_buffer.split("\n", 1)
            line = line.strip()
            if line:
                handle_serial_line(line)

    update_border_animation()


# ---- Dialogs ----
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


class ColorSettingsDialog(QDialog):
    PATTERN_LABELS = {
        "solid": "Solid Color",
        "breathing": "Breathing",
        "rainbow_wave": "Rainbow Wave",
        "color_cycle": "Color Cycle",
    }
    PATTERN_KEYS = {v: k for k, v in PATTERN_LABELS.items()}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Settings")

        self.pattern_box = QComboBox()
        self.pattern_box.addItems(list(self.PATTERN_LABELS.values()))
        current_pattern = config["settings"]["led_pattern"]
        self.pattern_box.setCurrentText(self.PATTERN_LABELS.get(current_pattern, "Rainbow Wave"))
        self.pattern_box.currentTextChanged.connect(self.on_pattern_changed)

        self.wheel = ColorWheel()
        r, g, b = config["settings"]["led_color"]
        self.wheel.set_color(r, g, b)

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(10, 150)
        self.brightness_slider.setValue(config["settings"]["led_brightness"])
        self.brightness_label = QLabel(str(self.brightness_slider.value()))
        self.brightness_slider.valueChanged.connect(lambda v: self.brightness_label.setText(str(v)))

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 100)
        self.speed_slider.setValue(config["settings"]["led_speed_percent"])
        self.speed_label = QLabel(f"{self.speed_slider.value()}%")
        self.speed_slider.valueChanged.connect(lambda v: self.speed_label.setText(f"{v}%"))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Pattern:"))
        layout.addWidget(self.pattern_box)
        layout.addWidget(QLabel("Color (used for Solid Color / Breathing):"))
        layout.addWidget(self.wheel)

        brightness_row = QHBoxLayout()
        brightness_row.addWidget(self.brightness_slider)
        brightness_row.addWidget(self.brightness_label)
        layout.addWidget(QLabel("Brightness:"))
        layout.addLayout(brightness_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)
        layout.addWidget(QLabel("Speed:"))
        layout.addLayout(speed_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.on_pattern_changed(self.pattern_box.currentText())

    def on_pattern_changed(self, text):
        needs_color = text in ("Solid Color", "Breathing")
        self.wheel.set_wheel_enabled(needs_color)

    def get_pattern_key(self):
        return self.PATTERN_KEYS[self.pattern_box.currentText()]

    def get_color(self):
        return list(self.wheel.get_color())


class EncoderConfigDialog(QDialog):
    def __init__(self, enc_id):
        super().__init__()
        self.enc_id = enc_id
        self.setWindowTitle(f"Encoder {enc_id}")

        target = config.get("encoders", {}).get(enc_id, {}).get("target", "system")
        is_app = target.startswith("app:")

        self.mode_box = QComboBox()
        self.mode_box.addItems(["Volume Geral", "Aplicativo"])
        self.mode_box.setCurrentIndex(1 if is_app else 0)
        self.mode_box.currentTextChanged.connect(self.on_mode_changed)

        self.exe_edit = QLineEdit()
        self.exe_edit.setReadOnly(True)
        if is_app:
            self.exe_edit.setText(target.split("app:", 1)[1])

        self.browse_button = QPushButton("Selecionar...")
        self.browse_button.clicked.connect(self.browse_for_exe)

        self.exe_edit.setEnabled(is_app)
        self.browse_button.setEnabled(is_app)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Encoder {enc_id} mode:"))
        layout.addWidget(self.mode_box)
        row = QHBoxLayout()
        row.addWidget(self.exe_edit)
        row.addWidget(self.browse_button)
        layout.addLayout(row)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def on_mode_changed(self, text):
        is_app = (text == "Aplicativo")
        self.exe_edit.setEnabled(is_app)
        self.browse_button.setEnabled(is_app)

    def browse_for_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar aplicativo", "", "Executáveis (*.exe)")
        if path:
            self.exe_edit.setText(os.path.basename(path))

    def get_target(self):
        if self.mode_box.currentText() == "Aplicativo":
            return f"app:{self.exe_edit.text()}"
        return "system"


# ---- Handlers ----
def on_button_clicked(idx):
    if idx == 15:
        on_settings_clicked()
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
        two_fx_state.timeout_seconds = dialog.timeout_spin.value()
        save_config()
        print("Settings saved")
    else:
        print("Settings cancelled")


def on_color_settings_clicked():
    dialog = ColorSettingsDialog()
    if dialog.exec():
        config["settings"]["led_pattern"] = dialog.get_pattern_key()
        config["settings"]["led_color"] = dialog.get_color()
        config["settings"]["led_brightness"] = dialog.brightness_slider.value()
        config["settings"]["led_speed_percent"] = dialog.speed_slider.value()

        send_led_command(f"LED:BRIGHTNESS:{dialog.brightness_slider.value()}")
        send_led_command(f"LED:SPEED:{percent_to_ms(dialog.speed_slider.value())}")

        save_config()
        if not two_fx_state.armed:
            apply_idle_led_pattern()
        print("Color settings saved")
    else:
        print("Color settings cancelled")


def on_encoder_clicked(enc_id):
    dialog = EncoderConfigDialog(enc_id)
    if dialog.exec():
        if "encoders" not in config:
            config["encoders"] = {}
        config["encoders"][enc_id] = {"target": dialog.get_target()}
        save_config()
        print(f"Encoder {enc_id} saved")
    else:
        print(f"Encoder {enc_id} config cancelled")


# ---- Main window ----
class MainWindow(QMainWindow):
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        tray_icon.showMessage(
            "Stream Deck Macro",
            "Still running in the background. Use the tray icon to reopen or quit.",
            QSystemTrayIcon.Information,
            2000,
        )


def reset_leds_and_disconnect():
    try:
        apply_idle_led_pattern()
        ser.close()
    except Exception:
        pass


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
app.aboutToQuit.connect(reset_leds_and_disconnect)

window = MainWindow()
window.setWindowTitle("Stream Deck Macro")
window.resize(560, 560)

central = QWidget()
outer_layout = QVBoxLayout()

border_widget = AnimatedBorder()

content_row = QHBoxLayout()

grid = QGridLayout()
for row in range(4):
    for col in range(4):
        idx = row * 4 + col
        label = "2FX" if idx == 15 else f"BTN{idx}"
        button = QPushButton(label)
        button.setMinimumSize(80, 80)
        button.clicked.connect(lambda checked=False, i=idx: on_button_clicked(i))
        grid.addWidget(button, row, col)
        button_widgets[idx] = button

content_row.addLayout(grid)
content_row.addSpacing(40)

encoder_column = QVBoxLayout()
encoder_column.addStretch()
for enc_id in ["1", "2", "3"]:
    enc_button = QPushButton(f"ENC{enc_id}")
    enc_button.setFixedSize(70, 70)
    enc_button.setStyleSheet("border-radius: 35px; background-color: #444; color: white;")
    enc_button.clicked.connect(lambda checked=False, e=enc_id: on_encoder_clicked(e))
    encoder_column.addWidget(enc_button)
    encoder_column.addStretch()

content_row.addLayout(encoder_column)
border_widget.inner_layout.addLayout(content_row)

color_settings_button = QPushButton("Color Settings")
color_settings_button.clicked.connect(on_color_settings_clicked)

outer_layout.addWidget(border_widget)
outer_layout.addWidget(color_settings_button)
central.setLayout(outer_layout)
window.setCentralWidget(central)

timer = QTimer()
timer.timeout.connect(poll_serial)
timer.start(50)

tray_pixmap = QPixmap(32, 32)
tray_pixmap.fill(QColor(80, 80, 200))
tray_icon = QSystemTrayIcon(QIcon(tray_pixmap))
tray_icon.setToolTip("Stream Deck Macro")

tray_menu = QMenu()
open_action = QAction("Open")
open_action.triggered.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
quit_action = QAction("Quit")
quit_action.triggered.connect(app.quit)
tray_menu.addAction(open_action)
tray_menu.addAction(quit_action)
tray_icon.setContextMenu(tray_menu)
tray_icon.activated.connect(
    lambda reason: (window.show(), window.raise_(), window.activateWindow())
    if reason == QSystemTrayIcon.Trigger else None
)
tray_icon.show()

window.show()
sys.exit(app.exec())
