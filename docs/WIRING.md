# Wiring

Physical wiring reference for the Pro Micro. Everything here is derived from
`firmware/stream_deck_macro.ino`, not from a diagram — if the firmware and
this file ever disagree, the firmware wins and this file is the bug.

## Button matrix

The firmware names these by **electrical role**, not "row"/"column", because
on the real build the two buses landed the opposite way round from what this
file originally assumed. There is no canonical assignment — the firmware has
to match the hardware.

`drivePins[4] = {10, 9, 8, 7}` are `OUTPUT`, idle `HIGH`, pulled `LOW` one at
a time during the scan. `readPins[4] = {6, 5, 4, 3}` are `INPUT_PULLUP` and
read `LOW` when a key on the active row is pressed.

**Both arrays run high-to-low on purpose.** The buses are landed on the pins
in the opposite order to the pad's own geometry, so ascending arrays put index
0 on the bottom-right key instead of the top-left one — the whole grid comes
out rotated 180 degrees (`reported = 15 - actual`). Reversing both arrays
fixes it without touching the `row*4+col` maths.

| matrix | pin | wire on the pad |
| --- | --- | --- |
| row 0, top (driven) | `D10` | bare bus, diode **cathode** |
| row 1 | `D9` | bare bus |
| row 2 | `D8` | bare bus |
| row 3, bottom | `D7` | bare bus |
| column 0, left (read) | `D6` | green, no diode |
| column 1 | `D5` | green |
| column 2 | `D4` | green |
| column 3, right | `D3` | green |

**Verified on hardware 2026-10-11**: pressing all sixteen keys left-to-right,
top-to-bottom produced `BTN:0` through `BTN:15` in exact order, with the 2FX
key landing on `BTN:15` as the app requires (it is the one key the app refuses
to let you assign an action to).

**The matrix uses no GND.** Rows drive, columns read through the internal
pull-ups, and each switch bridges a row and a column through its diode. All
three GND pins stay free for the encoders and the LEDs.

### Button numbering

`scanMatrix()` computes `idx = r * 4 + c` and emits `BTN:<idx>:DOWN|UP`, so
the row and column order decides which physical key is which button in the
app. Wire them in this order or the grid comes out scrambled:

|  | `D7` | `D8` | `D9` | `D10` |
| --- | --- | --- | --- | --- |
| **`D3`** | 0 | 1 | 2 | 3 |
| **`D4`** | 4 | 5 | 6 | 7 |
| **`D5`** | 8 | 9 | 10 | 11 |
| **`D6`** | 12 | 13 | 14 | 15 |

### Diode orientation

**The diode cathode (painted band) goes to the DRIVEN bus** — the one on
`D7`–`D10`. The anode side reaches the switch, whose other pin goes to a read
pin on `D3`–`D6`.

The reason, so it can be re-derived instead of trusted: a read pin sits at 5 V
through its internal pull-up and the active driven pin is held at 0 V, so
current flows **read pin → switch → diode anode → cathode → driven pin**. A
diode only conducts anode → cathode.

**This is the failure that actually happened on 2026-10-11.** The bare bus
carrying the cathodes was landed on the pins the firmware holds at 5 V, which
reverse-biases every diode. The symptom is distinctive and worth recognising:
**all sixteen keys silent — not scrambled, silent.** Scrambled indices mean a
swap somewhere; total silence means nothing can conduct at all.

The fix was two lines of firmware (swapping the pin arrays), not unsoldering
sixteen diodes. The diodes were correct the whole time relative to the
switches; only the bus-to-pin assignment was reversed.

## Encoders

Three EC11-style incremental encoders with a push-button, numbered
**top-to-bottom as they sit on the deck** — ENC1 at the top. That is also the
order `app.py` draws them in its encoder column, so the whole project reads
the same way round.

| encoder | `clk` | `dt` | `sw` | wire colours (dt / clk / sw) |
| --- | --- | --- | --- | --- |
| ENC1 | `D1` / `TX0` | `A3` | `A2` | purple / gray / white |
| ENC2 | `D0` / `RXI` | `A1` | `A0` | black / brown / red |
| ENC3 | `D2` | `D15` | `D14` | orange / yellow / green |

GND bus: **blue**.

**The pin map follows the deck's physical order on purpose.** ENC1 takes the
topmost pins on both edges, ENC3 the lowest. This was reassigned on
2026-10-12, after the wire colours were chosen — ENC1 used to be on
`0`/`A0`/`A1`. Nothing was given up: `dt` and `sw` are plain reads with no
timing requirement, so which of `A0`–`A3`/`D14`/`D15` each one gets is
arbitrary, and the three `clk` pins are interchangeable interrupt pins
(`INT3`, `INT2`, `INT1`).

**The CLK assignment is forced, not chosen.** On the ATmega32U4 only five
pins can raise an external interrupt — `0, 1, 2, 3, 7` — and `3` and `7` are
already matrix pins. That leaves exactly `0`, `1` and `2` for three encoders'
clocks. An encoder clock has to be interrupt-driven: polled from the main
loop it drops steps as soon as the knob is turned quickly.

**`D0` and `D1` are safe to use as GPIO here.** They carry `Serial1`, the
hardware UART, which this project never uses — the host link is USB CDC, a
separate peripheral on the 32U4. Nothing is sacrificed by putting encoder
clocks there.

### The wire colours and why they shape the map

The nine colours are a 10-way rainbow flat cut into three triples, each
triple in `dt, clk, sw` order:

| strands | colours | encoder |
| --- | --- | --- |
| 1–3 | black, brown, red | ENC2 |
| 4–6 | orange, yellow, green | ENC3 |
| 7 | blue | GND bus (the leftover strand) |
| 8–10 | purple, gray, white | ENC1 |

With the map above, **the middle wire of each triple is the `clk`** and is
the only one that crosses to the left edge; the two outer wires land on
adjacent pins down the right edge, in cable order, with `dt` above `sw`.

### Where the wires land

| left edge, top to bottom | signal | colour |
| --- | --- | --- |
| `TX0` / `D1` | ENC1 clk | gray |
| `RXI` / `D0` | ENC2 clk | brown |
| `GND` | encoder ground bus | blue |
| `GND` | spare | — |
| `D2` | ENC3 clk | yellow |

| right edge, top to bottom | signal | colour |
| --- | --- | --- |
| `A3` | ENC1 dt | purple |
| `A2` | ENC1 sw | white |
| `A1` | ENC2 dt | black |
| `A0` | ENC2 sw | red |
| `D15` | ENC3 dt | orange |
| `D14` | ENC3 sw | green |

The left edge therefore splits cleanly: the **top five pins are the encoder
zone**, the **bottom seven are the matrix**.

### Ground

An EC11 needs ground twice: the rotary section's common terminal (the middle
of the three pins on that side) and one of the two switch terminals. Three
encoders is six ground connections, and the board has only three GND pins —
so run a **shared ground bus** on the blue strand and daisy-chain it, exactly
like the matrix's bare bus.

| GND pin | position | use |
| --- | --- | --- |
| GND | left edge, 3rd from top | encoder ground bus (all six connections) |
| GND | left edge, 4th from top | spare — split the bus here if it is easier |
| GND | right edge, 2nd from top | LED strip ground |

`VCC` (right edge, 4th from top) feeds the LED strip. **The encoders need no
VCC** if they are bare EC11s: the firmware sets `clk`, `dt` and `sw` to
`INPUT_PULLUP`, so the chip's own pull-ups do the job and each terminal only
ever has to be pulled down to ground.

If what you have is a **KY-040 breakout module** instead of a bare encoder —
a small green PCB with five pins labelled `CLK DT SW + GND` — the three
signals and GND go exactly where the table says, and the `+` pin goes to
`VCC`. The module's onboard pull-ups sit in parallel with the internal ones,
which is harmless.

### Terminal map on the encoder itself

A bare EC11 has three pins on one side and two on the other:

| terminal | goes to |
| --- | --- |
| A (outer, 3-pin side) | `clk` pin |
| C (middle, 3-pin side) | ground bus |
| B (outer, 3-pin side) | `dt` pin |
| either switch pin | `sw` pin |
| the other switch pin | ground bus |

**Verified on hardware 2026-10-12.** All three encoders turn both ways in the
correct direction, push to mute, and emit exactly one event per detent
(counted runs of ten clicks gave exactly ten events each way). The direction
sign and the decoder both had to be corrected to get there — see the
"Encoder decoder" section in `CLAUDE.md` for what failed and why.

**A and B are interchangeable** — swapping them only reverses which direction
counts as clockwise. That is a one-line firmware fix (the `encDelta[i]--` and
`encDelta[i]++` branches in `encTick()` trade places), not a resoldering job,
so do not agonise over which outer pin is which. The middle pin is the one
that must be right.

## LED strip

A single chain of WS2812B-family addressable LEDs on one data pin. The unit
on the bench carries **5 LEDs** (a cut section); the intended final build is
one per key, 16 in total. `NUM_LEDS` in the firmware is the only place that
number lives.

| strip pad | pin | position | wire colour |
| --- | --- | --- | --- |
| `5V` / `+` | `VCC` | right edge, 4th from top | blue |
| `DIN` | `D16` | right edge, 11th from top | dark green |
| `GND` | `GND` | right edge, 2nd from top | — |

`D16` is the **second pin up from the bottom of the right edge**, directly
above `D10` (the matrix's fourth driven line). Those two are neighbours, so
check the silk rather than counting — landing the data line on `D10` would
break four keys and leave the strip dark, with nothing to point at the cause.

**Mind the arrows on the strip.** WS2812B is directional: data enters at
`DIN` and leaves at `DOUT`, and the arrows printed between the pads show
which way. Feeding the `DOUT` end lights nothing at all, with no other
symptom.

**Power comes from `VCC`, not `RAW`.** `VCC` is the regulated 5 V rail;
`RAW` is the unregulated USB input ahead of the regulator. At the firmware's
default brightness cap (50 of 255) five LEDs draw roughly 60 mA, and even at
full white they would draw about 300 mA — inside the 500 mA USB budget, but
the cap is what keeps it there, so do not raise `setBrightness()` past 50
without recounting.

### The resistor and the capacitor

Two parts that are not optional on the final build and are merely advisable
on this one:

- **~330 Ω in series on the data line**, as close to the first LED as the
  layout allows. It damps the reflection on the rising edge, which is what
  corrupts the first pixel's bits on anything longer than a few centimetres.
- **~1000 µF across 5 V and GND** near the first LED. It absorbs the inrush
  when the whole chain changes colour at once, which otherwise browns out the
  rail for a few microseconds.

With 5 LEDs on short leads both can be skipped and it will usually work.
With 16 they are the difference between a strip that behaves and one that
flickers intermittently and gets blamed on the firmware.

### Colour order — settled

`NEO_GRB`, confirmed on the real strip on 2026-10-12: asked for solid red and
red came out. `CLAUDE.md` had long claimed a bench test showed `NEO_RGB`;
that note was the stale side of the contradiction and has been corrected.

Red is the request that discriminates. With the strip declared `NEO_GRB` the
library transmits G,R,B = `0,255,0`, so RGB hardware would have shown green.
Blue proves nothing — it is the last byte in both orders and looks the same
either way.

Re-verify per batch if the LED source changes.

## Physical layout on the board

The matrix occupies **seven consecutive pins down the left edge** (`D3`
through `D9`); only column 3 (`D10`) sits on the other side, at the bottom of
the right edge, directly across from `D9`. A seven-way ribbon down the left
plus one jumper across covers the whole matrix.

| left edge, USB at top | right edge, USB at top |
| --- | --- |
| `TX0`/`D1` — ENC1 clk | `RAW` |
| `RXI`/`D0` — ENC2 clk | `GND` |
| `GND` | `RST` |
| `GND` | `VCC` |
| `D2` — ENC3 clk | `A3` — ENC1 dt |
| **`D3` — row 0** | `A2` — ENC1 sw |
| **`D4` — row 1** | `A1` — ENC2 dt |
| **`D5` — row 2** | `A0` — ENC2 sw |
| **`D6` — row 3** | `D15` — ENC3 dt |
| **`D7` — column 0** | `D14` — ENC3 sw |
| **`D8` — column 1** | `D16` — LED data |
| **`D9` — column 2** | **`D10` — column 3** |

> **Confirmed on the real board, 2026-10-11.** This order was originally
> written from the commonly published SparkFun layout without a primary
> source — SparkFun ships the pinout only as an image — and was marked
> unverified. It has since been checked against the silkscreen of the actual
> board and photographed: the top edge reads `RAW GND RST VCC A3 A2 …` and the
> bottom edge `TXO RXI GND GND 2 3 …`, exactly as above.
>
> Still worth knowing: **the `D14` silkscreen label changed between board
> revisions**, which will matter when ENC3 is wired.

## What not to encroach on

`D2`, immediately above `D3`, is ENC3's clock. Starting the matrix one pin
higher would silently break encoder 3. Everything above `D10` on the right
edge is already allocated too — see the table above and the closed pin map in
`CLAUDE.md`.

There are no spare pins: all 18 are assigned.
