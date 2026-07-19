import json
import time
import pyautogui

def execute_action(action):
    if action["type"] == "keyboard":
        keys = action["value"].split("+")
        pyautogui.hotkey(*keys)
    elif action["type"] == "empty":
        pass
    else:
        print(f"Action type '{action['type']}' not implemented yet")

with open("config.json", "r") as f:
    config = json.load(f)

action = config["buttons"]["0"]["layer1"]

print("Select some text somewhere — 3 seconds...")
time.sleep(3)
execute_action(action)
print("Done — check your clipboard.")