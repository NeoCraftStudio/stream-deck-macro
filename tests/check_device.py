import sounddevice as sd

info = sd.query_devices(23)
print(info)