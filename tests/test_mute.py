from pycaw.pycaw import AudioUtilities

TARGET = "opera.exe"

sessions = AudioUtilities.GetAllSessions()
for session in sessions:
    if session.Process and session.Process.name().lower() == TARGET.lower():
        session.SimpleAudioVolume.SetMute(0, None)
        print(f"Unmuted {TARGET}")