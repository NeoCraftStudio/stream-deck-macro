import sounddevice as sd
import numpy as np

DEVICE = 23  # CABLE Input, WASAPI
SAMPLE_RATE = 48000
DURATION = 2

t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), endpoint=False)
tone = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone

sd.play(tone, samplerate=SAMPLE_RATE, device=DEVICE)
sd.wait()
print("Done")