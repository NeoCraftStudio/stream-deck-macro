#include <Adafruit_NeoPixel.h>

// Identity string for the "ID?" handshake — app.py matches on this exact
// string (see DEVICE_ID_RESPONSE in app.py) to confirm it's actually
// talking to THIS project's firmware, not just any board that shares the
// same USB VID:PID (which only identifies the Pro Micro model, not the
// specific device/project running on it).
#define DEVICE_ID "ID:NEOCRAFT_MACRO_DESK:v1"

// ---- Button matrix ----
// Named by ELECTRICAL ROLE, not "row"/"column", because on the real build the
// bus carrying the diode cathodes turned out to be the pad's column, not its
// row. There is no canonical assignment — the firmware has to match the
// hardware, and renaming these made that impossible to get backwards again.
//
// drivePins idle HIGH and are pulled LOW one at a time. readPins sit on the
// internal pull-ups. Current runs readPin (5 V) -> switch -> diode anode ->
// cathode -> drivePin (0 V), which is the only direction a diode conducts.
// Wired the other way round the diode is reverse-biased and ALL 16 keys stay
// silent — not scrambled, silent. That was the real fault on 2026-10-11:
// the bare (cathode) bus had been landed on D7-D10, which the firmware holds
// at 5 V, so nothing could ever conduct.
// Which axis each bus physically selects, AND which end of each bus is index
// 0, were both established by measurement rather than by reading the wiring.
// Pressing left-to-right across the pad changes the READ index; pressing
// top-to-bottom changes the DRIVEN one.
//
// Both arrays run high-to-low because the buses are landed on the pins in the
// opposite order to the pad's own geometry. Measured 2026-10-11: with the
// arrays ascending, the 2FX key (BTN:15, bottom-right) reported BTN:0 and its
// neighbour reported BTN:1 - the whole grid came out rotated 180 degrees,
// reported = 15 - actual. Reversing both arrays maps index 0 back onto the
// top-left key without touching the row*4+col maths.
const int drivePins[4] = {10, 9, 8, 7};  // pad ROWS — bare wire, diode cathode
const int readPins[4]  = {6, 5, 4, 3};   // pad COLUMNS — green wire, no diode
bool btnState[16] = {false};
unsigned long lastChangeTime[16] = {0};
const unsigned long DEBOUNCE_MS = 30;

// ---- Encoders ----
// Three EC11s, numbered top-to-bottom as they sit on the deck (ENC1 at the
// top), which is also the order app.py draws them in its encoder column.
//
// The pin map follows that physical order on purpose, so the board reads the
// same way round as the deck: ENC1 takes the topmost pins on BOTH edges,
// ENC3 the lowest. Reassigned on 2026-10-12 - ENC1 used to be on 0/A0/A1 -
// after the wire colours were chosen. Nothing is lost by it: DT and SW are
// plain reads with no timing requirement, so which of A0-A3/14/15 each one
// gets is arbitrary, and all three CLK pins are interchangeable interrupt
// pins (INT3, INT2, INT1). What IS gained is that each encoder's three-wire
// ribbon segment lands as a contiguous, in-order group.
//
// Wire colours (a 10-way rainbow flat cut into three triples, each triple in
// DT, CLK, SW order):
//   ENC1  dt purple  clk gray   sw white
//   ENC2  dt black   clk brown  sw red
//   ENC3  dt orange  clk yellow sw green
//   GND bus: blue (the one unused strand)
// The MIDDLE wire of each triple is the CLK and is the one that crosses to
// the left edge; the two outer wires land on adjacent pins down the right.
//
// CLK must be interrupt-driven: polled from loop() an encoder drops steps as
// soon as the knob is turned quickly. On the ATmega32U4 only 0, 1, 2, 3 and
// 7 can raise an external interrupt, and 3 and 7 are matrix pins - so these
// three CLK pins are forced, not chosen.
const int ENC_CLK[3] = {1, 0, 2};        // D1/TX0, D0/RXI, D2 - left edge
const int ENC_DT[3]  = {A3, A1, 15};     // D15 is ENC3's dt
const int ENC_SW[3]  = {A2, A0, 14};     // D14 is ENC3's sw
volatile int encDelta[3] = {0, 0, 0};
volatile uint8_t encLastCLK[3];
volatile int8_t encPending[3] = {0, 0, 0};
volatile unsigned long encLastTime[3] = {0, 0, 0};
// Only long enough to collapse sub-millisecond contact chatter. The old
// value was 5000 us, which is longer than the gap between the two CLK edges
// of one detent on a fast turn - it threw away real steps. Bounce rejection
// is now the decoder's job (see encTick), not a timer's.
const unsigned long ENC_CHATTER_US = 1000;
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
// Number of LEDs actually wired on THIS unit. Everything downstream scales
// off it (the rainbow spreads its hue range across NUM_LEDS, every effect
// loops to it), so this is the only place it needs changing.
// Currently 5: a cut section of strip, confirmed by the user on 2026-10-11.
// A full build is one LED per key (16) — but do not "fix" this to 16 without
// the hardware to match, or eleven of them will simply never light.
#define NUM_LEDS 5

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

enum LedMode { MODE_SOLID, MODE_BREATHE, MODE_RAINBOWWAVE, MODE_COLORCYCLE };
LedMode currentMode = MODE_RAINBOWWAVE;
uint8_t breatheR = 255, breatheG = 0, breatheB = 0;
uint16_t animSpeedMs = 20;
unsigned long lastAnimStep = 0;
uint32_t rainbowHue = 0;
int breathePhase = 0;
bool breatheIncreasing = true;

// Shared body for all three encoder interrupts. attachInterrupt() takes a
// plain function pointer with no argument, so each encoder needs its own
// one-line stub to pass its index in.
//
// One step is emitted per COMPLETE CLK cycle, and only when both halves of
// that cycle agree on the direction. The interrupt fires on CHANGE, so each
// detent is seen twice: once when CLK falls and once when it rises. On a
// falling edge a high DT means clockwise; on a rising edge the same DT level
// means the opposite, because the edge itself carries a sign. Two readings
// that disagree are discarded.
//
// That is what makes this bounce-proof, and it is why the old version was
// not. Contact chatter on CLK produces extra edges while DT sits still, so
// the bounced edge computes the OPPOSITE direction to the real one, the two
// halves disagree, and the step is thrown away instead of counted. Measured
// on hardware 2026-10-12: the previous single-edge decoder emitted two CW
// events in the middle of one continuous counter-clockwise turn of ENC3, and
// roughly four events per detent on all three knobs.
//
// Direction sign established by measurement, not derived: with the old
// decoder, turning clockwise reported CCW on all three encoders, so the
// mapping below is the old one inverted. All three agreed, which is expected
// - the A and B terminals were landed the same way round on all of them.
void encTick(uint8_t i) {
  unsigned long now = micros();
  if (now - encLastTime[i] < ENC_CHATTER_US) return;

  uint8_t clk = digitalRead(ENC_CLK[i]);
  if (clk == encLastCLK[i]) return;
  encLastCLK[i] = clk;
  encLastTime[i] = now;

  uint8_t dt = digitalRead(ENC_DT[i]);
  int8_t dir = (clk == LOW) ? (dt ? 1 : -1) : (dt ? -1 : 1);

  if (clk == LOW) {
    encPending[i] = dir;
  } else if (encPending[i] != 0) {
    if (encPending[i] == dir) {
      encDelta[i] += dir;
    }
    encPending[i] = 0;
  }
}

void enc1ISR() { encTick(0); }
void enc2ISR() { encTick(1); }
void enc3ISR() { encTick(2); }

void setup() {
  Serial.begin(9600);
  lastHostContact = millis();

  for (int i = 0; i < 4; i++) {
    pinMode(drivePins[i], OUTPUT);
    digitalWrite(drivePins[i], HIGH);
  }
  for (int i = 0; i < 4; i++) {
    pinMode(readPins[i], INPUT_PULLUP);
  }

  for (uint8_t i = 0; i < 3; i++) {
    pinMode(ENC_CLK[i], INPUT_PULLUP);
    pinMode(ENC_DT[i], INPUT_PULLUP);
    pinMode(ENC_SW[i], INPUT_PULLUP);
    encLastCLK[i] = digitalRead(ENC_CLK[i]);
    encPending[i] = 0;
  }
  attachInterrupt(digitalPinToInterrupt(ENC_CLK[0]), enc1ISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_CLK[1]), enc2ISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_CLK[2]), enc3ISR, CHANGE);

  strip.begin();
  strip.setBrightness(50);
  strip.show();
}

void loop() {
  scanMatrix();
  handleEncoders();
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
  for (int row = 0; row < 4; row++) {
    digitalWrite(drivePins[row], LOW);
    for (int col = 0; col < 4; col++) {
      // Row-major, so BTN:n runs left-to-right then top-to-bottom and matches
      // the grid the app draws. Measured on hardware: the first firmware fix
      // swapped the pin arrays AND flipped this index, which was one change
      // too many — the pad came out transposed (right went 0,4,8,12 instead
      // of 0,1,2,3). Swapping the arrays alone is the whole correction.
      int idx = row * 4 + col;
      bool pressed = (digitalRead(readPins[col]) == LOW);
      if (pressed != btnState[idx] && (millis() - lastChangeTime[idx]) > DEBOUNCE_MS) {
        btnState[idx] = pressed;
        lastChangeTime[idx] = millis();
        Serial.print("BTN:");
        Serial.print(idx);
        Serial.println(pressed ? ":DOWN" : ":UP");
      }
    }
    digitalWrite(drivePins[row], HIGH);
  }
}

void handleEncoders() {
  static bool lastSW[3] = {false, false, false};
  static unsigned long lastSWChangeTime[3] = {0, 0, 0};

  for (uint8_t i = 0; i < 3; i++) {
    noInterrupts();
    int delta = encDelta[i];
    encDelta[i] = 0;
    interrupts();

    if (delta != 0) {
      Serial.print("ENC:");
      Serial.print(i + 1);
      Serial.println(delta > 0 ? ":CW" : ":CCW");
    }

    bool sw = (digitalRead(ENC_SW[i]) == LOW);
    if (sw != lastSW[i] && (millis() - lastSWChangeTime[i]) > SW_DEBOUNCE_MS) {
      lastSW[i] = sw;
      lastSWChangeTime[i] = millis();
      if (sw) {
        Serial.print("ENC:");
        Serial.print(i + 1);
        Serial.println(":PUSH");
      }
    }
  }
}

void handleSerialCommand() {
  if (Serial.available() == 0) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  lastHostContact = millis();

  if (cmd == "ID?") {
    // Identity handshake — lets the host tell this board apart from any
    // other Pro Micro that happens to be plugged in at the same time
    // (same USB VID:PID, since that only identifies the board MODEL, not
    // this specific device/project). See DEVICE_ID above.
    Serial.println(DEVICE_ID);

  } else if (cmd.startsWith("LED:MODE:SOLID:")) {
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
