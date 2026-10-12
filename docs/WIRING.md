# Wiring

Physical wiring reference for the Pro Micro. Everything here is derived from
`firmware/stream_deck_macro.ino`, not from a diagram — if the firmware and
this file ever disagree, the firmware wins and this file is the bug.

## Button matrix

The firmware names these by **electrical role**, not "row"/"column", because
on the real build the two buses landed the opposite way round from what this
file originally assumed. There is no canonical assignment — the firmware has
to match the hardware.

`drivePins[4] = {7, 8, 9, 10}` are `OUTPUT`, idle `HIGH`, pulled `LOW` one at
a time during the scan. `readPins[4] = {3, 4, 5, 6}` are `INPUT_PULLUP` and
read `LOW` when a key on the active row is pressed.

| matrix | pin | wire on the pad |
| --- | --- | --- |
| row 0 (driven) | `D7` | bare bus, diode **cathode** |
| row 1 | `D8` | bare bus |
| row 2 | `D9` | bare bus |
| row 3 | `D10` | bare bus |
| column 0 (read) | `D3` | green, no diode |
| column 1 | `D4` | green |
| column 2 | `D5` | green |
| column 3 | `D6` | green |

**Verified on hardware 2026-10-11**: pressing all sixteen keys left-to-right,
top-to-bottom produced `BTN:0` through `BTN:15` in exact order.

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

## Physical layout on the board

The matrix occupies **seven consecutive pins down the left edge** (`D3`
through `D9`); only column 3 (`D10`) sits on the other side, at the bottom of
the right edge, directly across from `D9`. A seven-way ribbon down the left
plus one jumper across covers the whole matrix.

| left edge, USB at top | right edge, USB at top |
| --- | --- |
| `TX0`/`D1` — ENC3 clk | `RAW` |
| `RXI`/`D0` — ENC1 clk | `GND` |
| `GND` | `RST` |
| `GND` | `VCC` |
| `D2` — ENC2 clk | `A3` — ENC2 sw |
| **`D3` — row 0** | `A2` — ENC2 dt |
| **`D4` — row 1** | `A1` — ENC1 sw |
| **`D5` — row 2** | `A0` — ENC1 dt |
| **`D6` — row 3** | `D15` — ENC3 sw |
| **`D7` — column 0** | `D14` — ENC3 dt |
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

`D2`, immediately above `D3`, is ENC2's clock. Starting the matrix one pin
higher would silently break encoder 2. Everything above `D10` on the right
edge is already allocated too — see the table above and the closed pin map in
`CLAUDE.md`.

There are no spare pins: all 18 are assigned.
