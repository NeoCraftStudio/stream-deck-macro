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
from PySide6.QtCore import QTimer, Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QImage, QPen, QIcon, QAction, QKeySequence,
    QPainterPath, QConicalGradient, QBrush,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QComboBox, QLineEdit, QDialogButtonBox, QLabel, QSpinBox,
    QKeySequenceEdit, QFileDialog, QSlider, QSystemTrayIcon, QMenu
)

APP_NAME = "NeoCraft Macro Desk"
# Keep in sync with MyAppVersion in installer/setup.iss — not read from
# there automatically, this is the one place app.py itself knows its version.
APP_VERSION = "2.1.1"
REPO_URL = "https://github.com/NeoCraftStudio/stream-deck-macro"
MANUAL_URLS = {
    "en": f"{REPO_URL}/blob/master/docs/MANUAL.md",
    "pt": f"{REPO_URL}/blob/master/docs/MANUAL_PT.md",
}


def resource_base_dir():
    # When packaged by PyInstaller (--onefile), sys.executable is the .exe
    # itself and relative paths must resolve next to IT, not to the
    # temporary folder PyInstaller unpacks into at runtime (that folder is
    # wiped after each run, so config.json would never actually persist).
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def bundled_resource_dir():
    # Read-only assets bundled into the exe (via --add-data) land in the
    # temp extraction folder at runtime, NOT next to the exe like
    # config.json — that's sys._MEIPASS for a --onefile build.
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def user_data_dir():
    # Where per-user, writable data (config.json) lives — independent of
    # where the app binary itself is installed. An installed app's own
    # folder isn't a safe place to write: Program Files needs admin, and
    # even a per-user install shouldn't assume its own directory stays
    # writable. %APPDATA% is the standard Windows location for this.
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA", BASE_DIR)
        path = os.path.join(base, APP_NAME)
        os.makedirs(path, exist_ok=True)
        return path
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = resource_base_dir()
ICON_PATH = os.path.join(bundled_resource_dir(), "assets", "icon.ico")
CONFIG_PATH = os.path.join(user_data_dir(), "config.json")
PORT = "COM5"
BAUD = 9600
VOLUME_STEP = 0.05

DEFAULT_CONFIG = {
    "settings": {
        "2fx_timeout_seconds": 10,
        "led_brightness": 50,
        "led_speed_percent": 50,
        "led_pattern": "rainbow_wave",
        "led_color": [255, 0, 0],
        "language": "pt",
    },
    "buttons": {},
    "encoders": {},
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

config["settings"].setdefault("led_brightness", 50)
config["settings"].setdefault("led_speed_percent", 50)
config["settings"].setdefault("led_pattern", "rainbow_wave")
config["settings"].setdefault("led_color", [255, 0, 0])
config["settings"].setdefault("language", "pt")


# ---- Translations ----
# Small hand-rolled dict instead of Qt's .ts/.qm Linguist workflow — this
# app's UI text is small and static enough that a lookup table is simpler
# to maintain than a separate translation-file toolchain. Dialogs are
# rebuilt from scratch every time they're opened, so they pick up a
# language change immediately; only widgets created once at startup (the
# "Color Settings" button, the tray menu) need an explicit refresh — see
# refresh_static_ui().
TR = {
    "configure_btn": {"en": "Configure BTN{idx}", "pt": "Configurar BTN{idx}"},
    "layer_label": {"en": "Layer:", "pt": "Camada:"},
    "layer1": {"en": "Layer 1", "pt": "Camada 1"},
    "layer2": {"en": "Layer 2 (2FX)", "pt": "Camada 2 (2FX)"},
    "action_type_label": {"en": "Action type:", "pt": "Tipo de ação:"},
    "action_type_keyboard": {"en": "Keyboard", "pt": "Teclado"},
    "action_type_macro": {"en": "Macro", "pt": "Macro"},
    "action_type_obs_scene": {"en": "OBS Scene", "pt": "Cena OBS"},
    "action_type_sound": {"en": "Sound", "pt": "Som"},
    "action_type_empty": {"en": "Empty", "pt": "Vazio"},
    "value_label": {"en": "Value:", "pt": "Valor:"},
    "browse": {"en": "Browse...", "pt": "Procurar..."},
    "sound_types_hint": {
        "en": "Supported: WAV, MP3, OGG, FLAC, AIFF",
        "pt": "Suportado: WAV, MP3, OGG, FLAC, AIFF",
    },
    "volume_label": {"en": "Volume:", "pt": "Volume:"},
    "trim_label": {"en": "Trim (drag the handles):", "pt": "Corte (arraste as alças):"},
    "play_preview": {"en": "▶ Play preview", "pt": "▶ Testar som"},
    "stop": {"en": "■ Stop", "pt": "■ Parar"},
    "select_sound_file": {"en": "Select sound file", "pt": "Selecionar arquivo de som"},
    "settings_title": {"en": "Settings", "pt": "Configurações"},
    "fx2_timeout_label": {
        "en": "Second-function wait time (seconds):",
        "pt": "Tempo de espera da segunda função (segundos):",
    },
    "language_label": {"en": "Language:", "pt": "Idioma:"},
    "color_settings_title": {"en": "Color Settings", "pt": "Configurações de Cor"},
    "pattern_label": {"en": "Pattern:", "pt": "Padrão:"},
    "pattern_solid": {"en": "Solid Color", "pt": "Cor Sólida"},
    "pattern_breathing": {"en": "Breathing", "pt": "Respiração"},
    "pattern_rainbow": {"en": "Rainbow Wave", "pt": "Onda Arco-íris"},
    "pattern_colorcycle": {"en": "Color Cycle", "pt": "Ciclo de Cor"},
    "color_used_for": {
        "en": "Color (used for Solid Color / Breathing):",
        "pt": "Cor (usada em Cor Sólida / Respiração):",
    },
    "brightness_label": {"en": "Brightness:", "pt": "Brilho:"},
    "speed_label": {"en": "Speed:", "pt": "Velocidade:"},
    "encoder_title": {"en": "Encoder {id}", "pt": "Encoder {id}"},
    "encoder_mode_label": {"en": "Encoder {id} mode:", "pt": "Modo do Encoder {id}:"},
    "mode_system": {"en": "System Volume", "pt": "Volume Geral"},
    "mode_app": {"en": "Application", "pt": "Aplicativo"},
    "select_ellipsis": {"en": "Select...", "pt": "Selecionar..."},
    "select_app_dialog_title": {"en": "Select application", "pt": "Selecionar aplicativo"},
    "executables_filter": {"en": "Executables (*.exe)", "pt": "Executáveis (*.exe)"},
    "color_settings_button": {"en": "Color Settings", "pt": "Configurações de Cor"},
    "settings_button": {"en": "Settings", "pt": "Configurações"},
    "help_button": {"en": "Help", "pt": "Ajuda"},
    "help_title": {"en": "Help", "pt": "Ajuda"},
    "version_label": {"en": "Version {version}", "pt": "Versão {version}"},
    "help_manual_link": {"en": "User Manual (GitHub)", "pt": "Manual do Usuário (GitHub)"},
    "help_repo_link": {"en": "GitHub Repository", "pt": "Repositório no GitHub"},
    "tray_open": {"en": "Open", "pt": "Abrir"},
    "tray_quit": {"en": "Quit", "pt": "Sair"},
    "tray_running_bg_msg": {
        "en": "Still running in the background. Use the tray icon to reopen or quit.",
        "pt": "Continua rodando em segundo plano. Use o ícone da bandeja para reabrir ou sair.",
    },
}


def tr(key, **kwargs):
    text = TR[key][config["settings"].get("language", "pt")]
    return text.format(**kwargs) if kwargs else text


def save_config():
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def percent_to_ms(percent):
    return round(60 - (percent / 100) * 55)


def led_cycle_increment():
    # Matches the firmware's real timing: a full hue rotation takes
    # 256 steps (65536 hue range / 256 per step) of animSpeedMs each.
    # The border animation ticks every 100ms (see animation_timer), so
    # this keeps the two in sync.
    ms_value = percent_to_ms(config["settings"]["led_speed_percent"])
    poll_interval_ms = 100
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
    with open(os.path.join(BASE_DIR, "tests", "obs_secrets.json"), "r") as f:
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
            start = action.get("sound_start")
            end = action.get("sound_end")
            if start or end:
                start_frame = int((start or 0) * samplerate)
                end_frame = int((end if end else len(data) / samplerate) * samplerate)
                data = data[start_frame:end_frame]
            volume = action.get("sound_volume", 100) / 100.0
            if volume != 1.0:
                data = data * volume
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


def get_app_sessions(process_name):
    # Multi-process apps (every Chromium-based browser, including Opera GX)
    # run one process per tab/renderer — all sharing the same exe name — so
    # matching only the first hit grabs an arbitrary process, usually not
    # the one actually making sound. Windows' own Volume Mixer shows these
    # grouped as a single app; matching (and adjusting) every session with
    # this process name is what makes that grouping actually work here.
    return [
        s for s in AudioUtilities.GetAllSessions()
        if s.Process and s.Process.name().lower() == process_name.lower()
    ]


def adjust_app_volume(process_name, delta):
    sessions = get_app_sessions(process_name)
    if not sessions:
        print(f"{process_name} not found among audio sessions")
        return
    new = None
    for session in sessions:
        vol = session.SimpleAudioVolume
        new = max(0.0, min(1.0, vol.GetMasterVolume() + delta))
        vol.SetMasterVolume(new, None)
    print(f"{process_name} volume: {int(new * 100)}% ({len(sessions)} process(es))")


def toggle_app_mute(process_name):
    sessions = get_app_sessions(process_name)
    if not sessions:
        print(f"{process_name} not found among audio sessions")
        return
    muted = sessions[0].SimpleAudioVolume.GetMute()
    new_mute = 0 if muted else 1
    for session in sessions:
        session.SimpleAudioVolume.SetMute(new_mute, None)
    print(f"{process_name} {'unmuted' if muted else 'muted'} ({len(sessions)} process(es))")


def handle_encoder_event(enc_id, event):
    flash_encoder(enc_id)
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
encoder_widgets = {}
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


def flash_encoder(enc_id):
    widget = encoder_widgets.get(enc_id)
    if widget is None:
        return
    widget.setStyleSheet("border-radius: 35px; background-color: #2ea043; color: white;")
    QTimer.singleShot(
        200,
        lambda: widget.setStyleSheet("border-radius: 35px; background-color: #444; color: white;"),
    )


def send_led_command(cmd):
    if ser is None or not ser.is_open:
        return
    try:
        ser.write((cmd + "\n").encode())
    except (serial.SerialException, OSError):
        pass


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
RAINBOW_GRADIENT_STOPS = 16  # color samples along the ring; Qt interpolates the rest in native code


class AnimatedBorder(QWidget):
    """Draws its border as a single stroked path, not per-segment lines — a rainbow
    needs a real color gradient along the stroke, so it uses QConicalGradient (built
    into Qt, evaluated in native code) instead of manually drawing hundreds of tiny
    colored line segments from Python every frame."""

    def __init__(self):
        super().__init__()
        self.hue_offset = 0.0
        self.mode = "rainbow"
        self.solid_color = QColor(255, 0, 0)
        self.inner_layout = QVBoxLayout()
        self.inner_layout.setContentsMargins(14, 14, 14, 14)
        self.setLayout(self.inner_layout)
        self._path = QPainterPath()
        self._path_rect = None

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

    def _border_path(self):
        rect = self.rect().adjusted(4, 4, -4, -4)
        if rect != self._path_rect:
            self._path = QPainterPath()
            self._path.addRoundedRect(QRectF(rect), 10, 10)
            self._path_rect = rect
        return self._path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = self._border_path()

        pen = QPen()
        pen.setWidth(6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        if self.mode == "rainbow":
            gradient = QConicalGradient(path.boundingRect().center(), self.hue_offset * 360)
            for i in range(RAINBOW_GRADIENT_STOPS + 1):
                frac = i / RAINBOW_GRADIENT_STOPS
                r, g, b = colorsys.hsv_to_rgb(frac, 1.0, 1.0)
                gradient.setColorAt(frac, QColor(int(r * 255), int(g * 255), int(b * 255)))
            pen.setBrush(QBrush(gradient))
        elif self.mode == "color_cycle":
            r, g, b = colorsys.hsv_to_rgb(self.hue_offset, 1.0, 1.0)
            pen.setColor(QColor(int(r * 255), int(g * 255), int(b * 255)))
        else:
            pen.setColor(self.solid_color)

        painter.setPen(pen)
        painter.drawPath(path)


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
ser = None
serial_buffer = ""
last_reconnect_attempt = 0.0
RECONNECT_INTERVAL_S = 2.0


def on_serial_connected():
    # Arduino resets when the port opens; give it a moment before writing.
    if ser is None or not ser.is_open:
        return
    send_led_command(f"LED:BRIGHTNESS:{config['settings']['led_brightness']}")
    send_led_command(f"LED:SPEED:{percent_to_ms(config['settings']['led_speed_percent'])}")
    apply_idle_led_pattern()


def connect_serial():
    global ser, serial_buffer
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0)
        serial_buffer = ""
        print(f"Connected to {PORT}")
        QTimer.singleShot(2000, on_serial_connected)
    except serial.SerialException:
        ser = None


connect_serial()


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
    global serial_buffer, ser, last_reconnect_attempt
    was_armed = two_fx_state.armed
    two_fx_state.check_timeout()
    if two_fx_state.armed != was_armed:
        set_2fx_override(two_fx_state.armed)
        update_all_button_styles()

    if ser is None:
        now = time.time()
        if now - last_reconnect_attempt >= RECONNECT_INTERVAL_S:
            last_reconnect_attempt = now
            connect_serial()
        return

    try:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
            serial_buffer += data
            while "\n" in serial_buffer:
                line, serial_buffer = serial_buffer.split("\n", 1)
                line = line.strip()
                if line:
                    handle_serial_line(line)
    except (serial.SerialException, OSError):
        print("Serial connection lost, will retry")
        try:
            ser.close()
        except Exception:
            pass
        ser = None


# ---- Dialogs ----
SOUND_FILE_FILTER = "Audio files (*.wav *.mp3 *.ogg *.flac *.aiff *.aif)"


class RangeTrimSlider(QWidget):
    """Two-handle bar for picking a start/end fraction (0.0-1.0) of a clip.
    Hand-rolled rather than a third-party range-slider package: the obvious
    one (QtRangeSlider) depends on `distutils`, removed from the stdlib in
    Python 3.12+, so it doesn't import at all on this project's Python 3.14."""

    rangeChanged = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(32)
        self.start = 0.0
        self.end = 1.0
        self._dragging = None
        self._margin = 9

    def set_range(self, start, end):
        self.start = max(0.0, min(start, end))
        self.end = min(1.0, max(end, start))
        self.update()

    def _pos_to_frac(self, x):
        span = max(1, self.width() - 2 * self._margin)
        return min(1.0, max(0.0, (x - self._margin) / span))

    def _frac_to_x(self, frac):
        span = self.width() - 2 * self._margin
        return self._margin + frac * span

    def mousePressEvent(self, event):
        frac = self._pos_to_frac(event.position().x())
        self._dragging = "start" if abs(frac - self.start) <= abs(frac - self.end) else "end"
        self._apply_drag(frac)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._apply_drag(self._pos_to_frac(event.position().x()))

    def mouseReleaseEvent(self, event):
        self._dragging = None

    def _apply_drag(self, frac):
        if self._dragging == "start":
            self.start = min(frac, self.end - 0.005)
        else:
            self.end = max(frac, self.start + 0.005)
        self.start = max(0.0, self.start)
        self.end = min(1.0, self.end)
        self.update()
        self.rangeChanged.emit(self.start, self.end)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        mid_y = self.height() // 2
        x0, x1 = self._frac_to_x(0), self._frac_to_x(1)
        xs, xe = self._frac_to_x(self.start), self._frac_to_x(self.end)

        track_pen = QPen(QColor("#666"), 4)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawLine(int(x0), mid_y, int(x1), mid_y)

        range_pen = QPen(QColor("#2ea043"), 4)
        range_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(range_pen)
        painter.drawLine(int(xs), mid_y, int(xe), mid_y)

        painter.setPen(QPen(QColor("white"), 1))
        painter.setBrush(QColor("#2ea043"))
        for x in (xs, xe):
            painter.drawEllipse(QPointF(x, mid_y), 8, 8)


class ConfigDialog(QDialog):
    ACTION_TYPES = ["keyboard", "macro", "obs_scene", "sound", "empty"]

    def __init__(self, btn_idx):
        super().__init__()
        self.btn_idx = btn_idx
        self.setWindowTitle(tr("configure_btn", idx=btn_idx))
        self._sound_duration = 0.0

        self.layer_box = QComboBox()
        self.layer_box.addItem(tr("layer1"), "layer1")
        self.layer_box.addItem(tr("layer2"), "layer2")
        self.layer_box.currentIndexChanged.connect(self.load_layer)

        self.type_box = QComboBox()
        for action_type in self.ACTION_TYPES:
            self.type_box.addItem(tr(f"action_type_{action_type}"), action_type)
        self.type_box.currentIndexChanged.connect(self.on_type_changed)

        self.value_label = QLabel(tr("value_label"))
        self.value_edit = QLineEdit()
        self.macro_edit = QKeySequenceEdit()
        self.macro_edit.hide()

        # ---- sound-specific widgets, shown only when action type == "sound" ----
        self.sound_path_edit = QLineEdit()
        self.sound_path_edit.setReadOnly(True)
        self.sound_browse_button = QPushButton(tr("browse"))
        self.sound_browse_button.clicked.connect(self.browse_for_sound)
        self.sound_types_label = QLabel(tr("sound_types_hint"))
        self.sound_types_label.setStyleSheet("color: gray; font-size: 11px;")

        self.sound_volume_title = QLabel(tr("volume_label"))
        self.sound_volume_slider = QSlider(Qt.Horizontal)
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setValue(100)
        self.sound_volume_label = QLabel("100%")
        self.sound_volume_slider.valueChanged.connect(
            lambda v: self.sound_volume_label.setText(f"{v}%")
        )

        self.sound_trim_title = QLabel(tr("trim_label"))
        self.sound_range = RangeTrimSlider()
        self.sound_range.rangeChanged.connect(lambda s, e: self._update_sound_range_label())
        self.sound_range_label = QLabel("0:00 - 0:00 / 0:00")
        self.sound_play_button = QPushButton(tr("play_preview"))
        self.sound_play_button.clicked.connect(self.play_sound_preview)
        self.sound_stop_button = QPushButton(tr("stop"))
        self.sound_stop_button.clicked.connect(self.stop_sound_preview)

        self.sound_widgets = [
            self.sound_path_edit, self.sound_browse_button, self.sound_types_label,
            self.sound_volume_title, self.sound_volume_slider, self.sound_volume_label,
            self.sound_trim_title, self.sound_range, self.sound_range_label,
            self.sound_play_button, self.sound_stop_button,
        ]

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(tr("layer_label")))
        layout.addWidget(self.layer_box)
        layout.addWidget(QLabel(tr("action_type_label")))
        layout.addWidget(self.type_box)
        layout.addWidget(self.value_label)
        layout.addWidget(self.value_edit)
        layout.addWidget(self.macro_edit)

        sound_path_row = QHBoxLayout()
        sound_path_row.addWidget(self.sound_path_edit)
        sound_path_row.addWidget(self.sound_browse_button)
        layout.addLayout(sound_path_row)
        layout.addWidget(self.sound_types_label)

        vol_row = QHBoxLayout()
        vol_row.addWidget(self.sound_volume_title)
        vol_row.addWidget(self.sound_volume_slider)
        vol_row.addWidget(self.sound_volume_label)
        layout.addLayout(vol_row)

        layout.addWidget(self.sound_trim_title)
        layout.addWidget(self.sound_range)
        layout.addWidget(self.sound_range_label)
        preview_row = QHBoxLayout()
        preview_row.addWidget(self.sound_play_button)
        preview_row.addWidget(self.sound_stop_button)
        layout.addLayout(preview_row)

        layout.addWidget(buttons)
        self.setLayout(layout)

        self.load_layer()  # populate fields from whatever is already saved

    def load_layer(self):
        layer = self.layer_box.currentData()
        saved = config["buttons"].get(str(self.btn_idx), {}).get(layer, {"type": "empty"})
        action_type = saved.get("type", "empty")

        self.type_box.blockSignals(True)
        self.type_box.setCurrentIndex(self.type_box.findData(action_type))
        self.type_box.blockSignals(False)
        self.on_type_changed()

        if action_type == "macro":
            self.macro_edit.setKeySequence(QKeySequence(saved.get("value", "")))
            self.value_edit.setText("")
        elif action_type == "sound":
            path = saved.get("value", "")
            self.sound_path_edit.setText(path)
            self._probe_sound_duration(path)
            self.sound_volume_slider.setValue(saved.get("sound_volume", 100))
            if self._sound_duration > 0:
                start = saved.get("sound_start", 0.0) / self._sound_duration
                end = saved.get("sound_end", self._sound_duration) / self._sound_duration
                self.sound_range.set_range(start, end)
            else:
                self.sound_range.set_range(0.0, 1.0)
            self._update_sound_range_label()
        else:
            self.value_edit.setText(saved.get("value", ""))
            self.macro_edit.setKeySequence(QKeySequence())

    def on_type_changed(self, _index=None):
        action_type = self.type_box.currentData()
        is_macro = (action_type == "macro")
        is_sound = (action_type == "sound")
        self.macro_edit.setVisible(is_macro)
        self.value_edit.setVisible(not is_macro and not is_sound)
        self.value_label.setVisible(not is_sound)
        for w in self.sound_widgets:
            w.setVisible(is_sound)

    def browse_for_sound(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("select_sound_file"), "", SOUND_FILE_FILTER)
        if path:
            self.sound_path_edit.setText(path)
            self._probe_sound_duration(path)
            self.sound_range.set_range(0.0, 1.0)
            self._update_sound_range_label()

    def _probe_sound_duration(self, path):
        try:
            info = sf.info(path)
            self._sound_duration = info.frames / info.samplerate
        except Exception as e:
            self._sound_duration = 0.0
            print(f"Couldn't read sound file info: {e}")

    def _update_sound_range_label(self):
        def fmt(s):
            return f"{int(s // 60)}:{int(s % 60):02d}"
        start_s = self.sound_range.start * self._sound_duration
        end_s = self.sound_range.end * self._sound_duration
        self.sound_range_label.setText(f"{fmt(start_s)} - {fmt(end_s)} / {fmt(self._sound_duration)}")

    def play_sound_preview(self):
        path = self.sound_path_edit.text()
        if not path:
            return
        try:
            data, samplerate = sf.read(path)
            start_frame = int(self.sound_range.start * self._sound_duration * samplerate)
            end_frame = int(self.sound_range.end * self._sound_duration * samplerate)
            data = data[start_frame:end_frame]
            volume = self.sound_volume_slider.value() / 100.0
            sd.play(data * volume, samplerate)
        except Exception as e:
            print(f"Preview failed: {e}")

    def stop_sound_preview(self):
        sd.stop()

    def get_value(self):
        if self.type_box.currentData() == "macro":
            return self.macro_edit.keySequence().toString().lower()
        if self.type_box.currentData() == "sound":
            return self.sound_path_edit.text()
        return self.value_edit.text()

    def get_sound_extra(self):
        return {
            "sound_volume": self.sound_volume_slider.value(),
            "sound_start": round(self.sound_range.start * self._sound_duration, 3),
            "sound_end": round(self.sound_range.end * self._sound_duration, 3),
        }


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("settings_title"))

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(config["settings"]["2fx_timeout_seconds"])

        # Language names are shown in their own language, not translated —
        # someone who can't read the current UI language still needs to
        # recognize "English"/"Português" to switch to a language they can.
        self.language_box = QComboBox()
        self.language_box.addItem("English", "en")
        self.language_box.addItem("Português", "pt")
        current_lang = config["settings"].get("language", "pt")
        self.language_box.setCurrentIndex(self.language_box.findData(current_lang))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(tr("fx2_timeout_label")))
        layout.addWidget(self.timeout_spin)
        layout.addWidget(QLabel(tr("language_label")))
        layout.addWidget(self.language_box)
        layout.addWidget(buttons)
        self.setLayout(layout)


class ColorSettingsDialog(QDialog):
    # config value -> translation key
    PATTERNS = {
        "solid": "pattern_solid",
        "breathing": "pattern_breathing",
        "rainbow_wave": "pattern_rainbow",
        "color_cycle": "pattern_colorcycle",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("color_settings_title"))

        self.pattern_box = QComboBox()
        for key, tr_key in self.PATTERNS.items():
            self.pattern_box.addItem(tr(tr_key), key)
        current_pattern = config["settings"]["led_pattern"]
        self.pattern_box.setCurrentIndex(self.pattern_box.findData(current_pattern))
        self.pattern_box.currentIndexChanged.connect(self.on_pattern_changed)

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
        layout.addWidget(QLabel(tr("pattern_label")))
        layout.addWidget(self.pattern_box)
        layout.addWidget(QLabel(tr("color_used_for")))
        layout.addWidget(self.wheel)

        brightness_row = QHBoxLayout()
        brightness_row.addWidget(self.brightness_slider)
        brightness_row.addWidget(self.brightness_label)
        layout.addWidget(QLabel(tr("brightness_label")))
        layout.addLayout(brightness_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)
        layout.addWidget(QLabel(tr("speed_label")))
        layout.addLayout(speed_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.on_pattern_changed()

    def on_pattern_changed(self, _index=None):
        needs_color = self.pattern_box.currentData() in ("solid", "breathing")
        self.wheel.set_wheel_enabled(needs_color)

    def get_pattern_key(self):
        return self.pattern_box.currentData()

    def get_color(self):
        return list(self.wheel.get_color())


class EncoderConfigDialog(QDialog):
    def __init__(self, enc_id):
        super().__init__()
        self.enc_id = enc_id
        self.setWindowTitle(tr("encoder_title", id=enc_id))

        target = config.get("encoders", {}).get(enc_id, {}).get("target", "system")
        is_app = target.startswith("app:")

        self.mode_box = QComboBox()
        self.mode_box.addItem(tr("mode_system"), "system")
        self.mode_box.addItem(tr("mode_app"), "app")
        self.mode_box.setCurrentIndex(1 if is_app else 0)
        self.mode_box.currentIndexChanged.connect(self.on_mode_changed)

        self.exe_edit = QLineEdit()
        self.exe_edit.setReadOnly(True)
        if is_app:
            self.exe_edit.setText(target.split("app:", 1)[1])

        self.browse_button = QPushButton(tr("select_ellipsis"))
        self.browse_button.clicked.connect(self.browse_for_exe)

        self.exe_edit.setEnabled(is_app)
        self.browse_button.setEnabled(is_app)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(tr("encoder_mode_label", id=enc_id)))
        layout.addWidget(self.mode_box)
        row = QHBoxLayout()
        row.addWidget(self.exe_edit)
        row.addWidget(self.browse_button)
        layout.addLayout(row)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def on_mode_changed(self, _index=None):
        is_app = (self.mode_box.currentData() == "app")
        self.exe_edit.setEnabled(is_app)
        self.browse_button.setEnabled(is_app)

    def browse_for_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("select_app_dialog_title"), "", tr("executables_filter"))
        if path:
            self.exe_edit.setText(os.path.basename(path))

    def get_target(self):
        if self.mode_box.currentData() == "app":
            return f"app:{self.exe_edit.text()}"
        return "system"


class HelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("help_title"))

        name_label = QLabel(f"<b>{APP_NAME}</b>")
        version_label = QLabel(tr("version_label", version=APP_VERSION))

        manual_url = MANUAL_URLS[config["settings"].get("language", "pt")]
        manual_link = QLabel(f'<a href="{manual_url}">{tr("help_manual_link")}</a>')
        manual_link.setOpenExternalLinks(True)
        repo_link = QLabel(f'<a href="{REPO_URL}">{tr("help_repo_link")}</a>')
        repo_link.setOpenExternalLinks(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(name_label)
        layout.addWidget(version_label)
        layout.addWidget(manual_link)
        layout.addWidget(repo_link)
        layout.addWidget(buttons)
        self.setLayout(layout)


# ---- Handlers ----
def on_button_clicked(idx):
    if idx == 15:
        # 2FX has no assignable action — it's the layer-toggle key, not a
        # mappable button. General settings live in their own button now
        # (see on_settings_clicked), so this tile is just a no-op.
        return

    dialog = ConfigDialog(idx)
    if dialog.exec():
        layer = dialog.layer_box.currentData()
        action_type = dialog.type_box.currentData()
        value = dialog.get_value()

        btn_key = str(idx)
        if btn_key not in config["buttons"]:
            config["buttons"][btn_key] = {
                "layer1": {"type": "empty"},
                "layer2": {"type": "empty"},
            }
        action = {"type": action_type, "value": value}
        if action_type == "sound":
            action.update(dialog.get_sound_extra())
        config["buttons"][btn_key][layer] = action
        save_config()
        print(f"Saved BTN{idx} [{layer}] = type={action_type}, value={value}")
    else:
        print(f"BTN{idx} config cancelled")


def on_settings_clicked():
    dialog = SettingsDialog()
    if dialog.exec():
        config["settings"]["2fx_timeout_seconds"] = dialog.timeout_spin.value()
        two_fx_state.timeout_seconds = dialog.timeout_spin.value()
        config["settings"]["language"] = dialog.language_box.currentData()
        save_config()
        refresh_static_ui()
        print("Settings saved")
    else:
        print("Settings cancelled")


def on_help_clicked():
    HelpDialog().exec()


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
            APP_NAME,
            tr("tray_running_bg_msg"),
            QSystemTrayIcon.Information,
            2000,
        )


def reset_leds_and_disconnect():
    try:
        apply_idle_led_pattern()
        if ser is not None:
            ser.close()
    except Exception:
        pass


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
app.aboutToQuit.connect(reset_leds_and_disconnect)

app_icon = QIcon(ICON_PATH)
app.setWindowIcon(app_icon)

window = MainWindow()
window.setWindowTitle(APP_NAME)
window.setWindowIcon(app_icon)
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
    encoder_widgets[enc_id] = enc_button
    encoder_column.addWidget(enc_button)
    encoder_column.addStretch()

content_row.addLayout(encoder_column)
border_widget.inner_layout.addLayout(content_row)

color_settings_button = QPushButton(tr("color_settings_button"))
color_settings_button.clicked.connect(on_color_settings_clicked)

settings_button = QPushButton(tr("settings_button"))
settings_button.clicked.connect(on_settings_clicked)

help_button = QPushButton(tr("help_button"))
help_button.clicked.connect(on_help_clicked)

bottom_row = QHBoxLayout()
bottom_row.addWidget(color_settings_button)
bottom_row.addWidget(settings_button)
bottom_row.addWidget(help_button)

outer_layout.addWidget(border_widget)
outer_layout.addLayout(bottom_row)
central.setLayout(outer_layout)
window.setCentralWidget(central)

timer = QTimer()
timer.timeout.connect(poll_serial)
timer.start(50)


def tick_animation():
    # Runs at its own (slower) rate, separate from the 50ms input-polling
    # timer above — the border color cycle doesn't need 20fps to look
    # smooth, and skipping it entirely while the window is hidden in the
    # tray means the background process isn't burning CPU on a repaint
    # nobody can see.
    if not window.isVisible():
        return
    update_border_animation()


animation_timer = QTimer()
animation_timer.timeout.connect(tick_animation)
animation_timer.start(100)


def send_heartbeat():
    # Firmware's disconnect watchdog needs a line at least once every 3s
    # (HOST_TIMEOUT_MS) or it shows solid red. Any command line resets that
    # timer on the firmware side, so idle periods need this dedicated ping.
    if ser is not None and ser.is_open:
        try:
            ser.write(b"PING\n")
        except (serial.SerialException, OSError):
            pass


heartbeat_timer = QTimer()
heartbeat_timer.timeout.connect(send_heartbeat)
heartbeat_timer.start(1000)

tray_icon = QSystemTrayIcon(app_icon)
tray_icon.setToolTip(APP_NAME)

tray_menu = QMenu()
open_action = QAction(tr("tray_open"))
open_action.triggered.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))
quit_action = QAction(tr("tray_quit"))
quit_action.triggered.connect(app.quit)
tray_menu.addAction(open_action)
tray_menu.addAction(quit_action)
tray_icon.setContextMenu(tray_menu)
tray_icon.activated.connect(
    lambda reason: (window.show(), window.raise_(), window.activateWindow())
    if reason == QSystemTrayIcon.Trigger else None
)
tray_icon.show()


def refresh_static_ui():
    # Everything else (dialogs) is rebuilt from scratch on each open and
    # picks up config["settings"]["language"] automatically — these
    # widgets are the only ones built once at startup, so a language
    # change needs to explicitly push new text into them.
    color_settings_button.setText(tr("color_settings_button"))
    settings_button.setText(tr("settings_button"))
    help_button.setText(tr("help_button"))
    open_action.setText(tr("tray_open"))
    quit_action.setText(tr("tray_quit"))

window.show()
sys.exit(app.exec())
