import json

with open("config.json", "r") as f:
    config = json.load(f)

print("2FX timeout:", config["settings"]["2fx_timeout_seconds"])

print("\nButtons:")
for btn_id, layers in config["buttons"].items():
    print(f"  Button {btn_id}:")
    print(f"    Layer 1: {layers['layer1']}")
    print(f"    Layer 2: {layers['layer2']}")

print("\nEncoders:")
for enc_id, data in config["encoders"].items():
    print(f"  Encoder {enc_id}: target = {data['target']}")