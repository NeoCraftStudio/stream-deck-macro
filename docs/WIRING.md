# Wiring

Physical wiring reference for the Pro Micro. Everything here is derived from
`firmware/stream_deck_macro.ino`, not from a diagram — if the firmware and
this file ever disagree, the firmware wins and this file is the bug.

## Button matrix

`rowPins[4] = {3, 4, 5, 6}` are `OUTPUT`, idle `HIGH`, pulled `LOW` one at a
time during the scan. `colPins[4] = {7, 8, 9, 10}` are `INPUT_PULLUP` and read
`LOW` when a key on the active row is pressed.

| matrix | pin |
| --- | --- |
| row 0 | `D3` |
| row 1 | `D4` |
| row 2 | `D5` |
| row 3 | `D6` |
| column 0 | `D7` |
| column 1 | `D8` |
| column 2 | `D9` |
| column 3 | `D10` |

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

**Anode on the column, cathode on the row** — the 1N4148's painted band faces
the row. This is the standard COL2ROW arrangement.

The reason, so it can be re-derived instead of trusted: the column sits at 5 V
through its internal pull-up and the active row is driven to 0 V, so current
flows **column → switch → row**. A diode only conducts anode → cathode.
Reversed, it blocks that current and no key ever registers.

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

> ⚠ **The physical order above is the common SparkFun layout and was NOT
> confirmed against a primary source** — SparkFun publishes the pinout only as
> an image. Confirm it against the silkscreen on the actual board before
> soldering. Note also that **the `D14` silkscreen label changed between board
> revisions**, which matters for ENC3 later.
>
> The *logical* assignment (which pin does what) is solid: it comes straight
> from the firmware. Only the left/right and top/bottom ordering is the
> unverified part.

## What not to encroach on

`D2`, immediately above `D3`, is ENC2's clock. Starting the matrix one pin
higher would silently break encoder 2. Everything above `D10` on the right
edge is already allocated too — see the table above and the closed pin map in
`CLAUDE.md`.

There are no spare pins: all 18 are assigned.
