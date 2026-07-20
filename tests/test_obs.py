import json
import obsws_python as obs

with open("tests/obs_secrets.json", "r") as f:
    secrets = json.load(f)

client = obs.ReqClient(host=secrets["host"], port=secrets["port"], password=secrets["password"])

client.set_current_program_scene("Test Scene 2")
print("Switched to Test Scene 2")