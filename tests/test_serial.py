import serial

PORT = "COM5"  # change to match your board's port
BAUD = 9600

ser = serial.Serial(PORT, BAUD, timeout=1)

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if line:
        print(line)