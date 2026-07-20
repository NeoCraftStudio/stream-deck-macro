import json
import time
import serial
import pyautogui

PORT = "COM5"
BAUD = 9600

with open("config.json", "r") as f:
    config = json.load(f)

TIMEOUT_SECONDS = config["settings"]["2fx_timeout_seconds"]


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


def execute_action(action):
    if action["type"] == "keyboard":
        keys = action["value"].split("+")
        pyautogui.hotkey(*keys)
        print(f"Executed keyboard: {action['value']}")
    elif action["type"] == "empty":
        pass
    else:
        print(f"Action type '{action['type']}' not implemented yet")


state = TwoFXState(TIMEOUT_SECONDS)
ser = serial.Serial(PORT, BAUD, timeout=0.2)

while True:
    state.check_timeout()

    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not line:
        continue

    if line.startswith("BTN:") and line.endswith(":DOWN"):
        btn_id = int(line.split(":")[1])
        layer = state.handle_button(btn_id)
        if layer is not None:
            btn_config = config["buttons"].get(str(btn_id))
            if btn_config:
                execute_action(btn_config[layer])