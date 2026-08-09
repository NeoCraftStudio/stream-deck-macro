#include <Adafruit_NeoPixel.h>

// ---- Button matrix ----
const int rowPins[4] = {3, 4, 5, 6};
const int colPins[4] = {7, 8, 9, 10};
bool btnState[16] = {false};
unsigned long lastChangeTime[16] = {0};
const unsigned long DEBOUNCE_MS = 30;

// ---- Encoder 1 ----
const int ENC1_CLK = 0;   // D0 / RXI
const int ENC1_DT  = A0;
const int ENC1_SW  = A1;
volatile int enc1Delta = 0;
volatile int enc1LastCLK;
volatile unsigned long enc1LastTime = 0;
const unsigned long ENC_DEBOUNCE_US = 5000;
const unsigned long SW_DEBOUNCE_MS = 30;

// ---- Host connection watchdog ----
// app.py sends "PING" once a second; if 3s pass with no line at all from
// the host, we assume it's gone (closed, crashed, or unplugged) and show
// solid red until it comes back.
unsigned long lastHostContact = 0;
const unsigned long HOST_TIMEOUT_MS = 3000;
bool hostConnected = true;

// ---- LEDs ----
#define LED_PIN 16
#define NUM_LEDS 9   // set to however many you have wired right now

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

enum LedMode { MODE_SOLID, MODE_BREATHE, MODE_RAINBOWWAVE, MODE_COLORCYCLE };
LedMode currentMode = MODE_RAINBOWWAVE;
uint8_t breatheR = 255, breatheG = 0, breatheB = 0;
uint16_t animSpeedMs = 20;
unsigned long lastAnimStep = 0;
uint32_t rainbowHue = 0;
int breathePhase = 0;
bool breatheIncreasing = true;

void enc1ISR() {
  unsigned long now = micros();
  if (now - enc1LastTime < ENC_DEBOUNCE_US) return;

  int clk = digitalRead(ENC1_CLK);
  if (clk != enc1LastCLK) {
    if (clk == LOW) {
      if (digitalRead(ENC1_DT) != clk) {
        enc1Delta--;
      } else {
        enc1Delta++;
      }
    }
    enc1LastCLK = clk;
    enc1LastTime = now;
  }
}

void setup() {
  Serial.begin(9600);
  lastHostContact = millis();

  for (int i = 0; i < 4; i++) {
    pinMode(rowPins[i], OUTPUT);
    digitalWrite(rowPins[i], HIGH);
  }
  for (int i = 0; i < 4; i++) {
    pinMode(colPins[i], INPUT_PULLUP);
  }

  pinMode(ENC1_CLK, INPUT_PULLUP);
  pinMode(ENC1_DT, INPUT_PULLUP);
  pinMode(ENC1_SW, INPUT_PULLUP);
  enc1LastCLK = digitalRead(ENC1_CLK);
  attachInterrupt(digitalPinToInterrupt(ENC1_CLK), enc1ISR, CHANGE);

  strip.begin();
  strip.setBrightness(50);
  strip.show();
}

void loop() {
  scanMatrix();
  handleEncoder();
  handleSerialCommand();
  checkHostConnection();
  updateLeds();
}

void checkHostConnection() {
  bool wasConnected = hostConnected;
  hostConnected = (millis() - lastHostContact) < HOST_TIMEOUT_MS;
  if (hostConnected == wasConnected) return;

  if (!hostConnected) {
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, strip.Color(255, 0, 0));
    }
    strip.show();
  }
  // Reconnecting doesn't need to do anything here — app.py re-sends the
  // real LED state right after opening the port (see on_serial_connected),
  // and updateLeds() below resumes its normal animation immediately since
  // it no longer sees currentMode forced to anything.
}

void scanMatrix() {
  for (int r = 0; r < 4; r++) {
    digitalWrite(rowPins[r], LOW);
    for (int c = 0; c < 4; c++) {
      int idx = r * 4 + c;
      bool pressed = (digitalRead(colPins[c]) == LOW);
      if (pressed != btnState[idx] && (millis() - lastChangeTime[idx]) > DEBOUNCE_MS) {
        btnState[idx] = pressed;
        lastChangeTime[idx] = millis();
        Serial.print("BTN:");
        Serial.print(idx);
        Serial.println(pressed ? ":DOWN" : ":UP");
      }
    }
    digitalWrite(rowPins[r], HIGH);
  }
}

void handleEncoder() {
  noInterrupts();
  int delta = enc1Delta;
  enc1Delta = 0;
  interrupts();

  if (delta > 0) {
    Serial.println("ENC:1:CW");
  } else if (delta < 0) {
    Serial.println("ENC:1:CCW");
  }

  static bool lastSW = false;
  static unsigned long lastSWChangeTime = 0;
  bool sw = (digitalRead(ENC1_SW) == LOW);
  if (sw != lastSW && (millis() - lastSWChangeTime) > SW_DEBOUNCE_MS) {
    lastSW = sw;
    lastSWChangeTime = millis();
    if (sw) {
      Serial.println("ENC:1:PUSH");
    }
  }
}

void handleSerialCommand() {
  if (Serial.available() == 0) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  lastHostContact = millis();

  if (cmd.startsWith("LED:MODE:SOLID:")) {
    int r, g, b;
    sscanf(cmd.c_str() + 15, "%d,%d,%d", &r, &g, &b);
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, strip.Color(r, g, b));
    }
    strip.show();
    currentMode = MODE_SOLID;

  } else if (cmd.startsWith("LED:MODE:BREATHE:")) {
    int r, g, b;
    sscanf(cmd.c_str() + 18, "%d,%d,%d", &r, &g, &b);
    breatheR = r; breatheG = g; breatheB = b;
    breathePhase = 0;
    breatheIncreasing = true;
    currentMode = MODE_BREATHE;

  } else if (cmd.startsWith("LED:MODE:RAINBOWWAVE")) {
    currentMode = MODE_RAINBOWWAVE;

  } else if (cmd.startsWith("LED:MODE:COLORCYCLE")) {
    currentMode = MODE_COLORCYCLE;

  } else if (cmd.startsWith("LED:BRIGHTNESS:")) {
    int val = cmd.substring(15).toInt();
    strip.setBrightness(val);

  } else if (cmd.startsWith("LED:SPEED:")) {
    int val = cmd.substring(10).toInt();
    animSpeedMs = val;
  }
}

void updateLeds() {
  if (!hostConnected) return;
  if (currentMode == MODE_SOLID) return;

  unsigned long now = millis();
  if (now - lastAnimStep < animSpeedMs) return;
  lastAnimStep = now;

  if (currentMode == MODE_RAINBOWWAVE) {
    for (int i = 0; i < NUM_LEDS; i++) {
      uint32_t pixelHue = rainbowHue + (i * 65536L / NUM_LEDS);
      strip.setPixelColor(i, strip.gamma32(strip.ColorHSV(pixelHue)));
    }
    strip.show();
    rainbowHue += 256;

  } else if (currentMode == MODE_COLORCYCLE) {
    uint32_t color = strip.gamma32(strip.ColorHSV(rainbowHue));
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, color);
    }
    strip.show();
    rainbowHue += 256;

  } else if (currentMode == MODE_BREATHE) {
    if (breatheIncreasing) {
      breathePhase += 5;
      if (breathePhase >= 250) breatheIncreasing = false;
    } else {
      breathePhase -= 5;
      if (breathePhase <= 5) breatheIncreasing = true;
    }
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, strip.Color(
        (breatheR * breathePhase) / 255,
        (breatheG * breathePhase) / 255,
        (breatheB * breathePhase) / 255
      ));
    }
    strip.show();
  }
}
