# Stream Deck Macro — project context for Claude

## Who's building this

Electrical/instrumentation engineer, beginner in programming. This project is
explicitly a **learning exercise**: the goal is to learn Git, GitHub, and
Python along the way — not just to reach a finished result. Prioritize
teaching over speed.

## How to work on this project

- Explain in 1-3 sentences what you're about to do and why, *before* doing it
  — especially for new Python concepts (classes, decorators, async, context
  managers, etc.). Explain the "why", not just the "how", without turning
  every reply into a lecture — follow the pace requested.
- **Never run git commands automatically or offer to.** The user runs
  `git init/add/commit/push` by hand, in the VS Code integrated terminal, as
  part of the learning process. When a git step is needed, describe what
  needs to happen conceptually and ask which command represents it; correct
  with an explanation if wrong, then wait for explicit confirmation before
  anything is actually run.
- **Never execute, build, delete, or modify anything without explicit
  permission.** Show paths/options and the next step, let the user decide.
- No praise on what the user writes or asks — be direct.
- Answers must be grounded in real sources (docs/API) — never invent library
  or API behavior.
- Don't assume automatic progression to the next step — the user signals when
  a topic is "under consideration" and resumes when ready.
- This project is also an **English practice** — correct English mistakes
  when they happen, set off in a blockquote (`>`) so it's visually distinct
  from the rest of the reply.
- **Format action steps separately from explanation** (requested 2026-07-19):
  put the "why"/explanation as prose first, then a clear separator, then the
  actual steps to do as a bare numbered list — no explanation mixed into the
  steps themselves. Keep step items to just the action, nothing else.
- **Always give the entire file, never partial snippets/diffs** (requested
  2026-07-19) — when Python code changes, paste the full, current contents
  of the file being edited, not just the changed piece. Applies to all code
  files in this project from here on.
- **No teaching for Arduino/C++ firmware code** (requested 2026-07-19) — the
  user does not want to learn Arduino/C++, only Git, GitHub, and Python (the
  original scope). For firmware work: just give the code and the steps, no
  concept explanations. Python still gets brief "why" context as before.

## Architecture (decided, closed)

### Hardware
- MCU: Arduino Pro Micro (ATmega32U4), **5V / 16MHz variant** (confirmed via
  crystal marking). No level shifter needed for the WS2812B LEDs — both run
  on 5V logic.
- 4x4 button matrix (16 positions = 15 buttons + 1 "2FX" key), 1N4148 diode
  per position, cathode toward the column (standard anti-ghosting).
- 3 incremental rotary encoders (KY-040/EC11) with push-button; each click =
  real mute (not zero-volume) of its associated audio channel.
- Individually addressable WS2812B-family LEDs, 1 per key, single chain on 1
  data pin (D16/MOSI); ~330Ω resistor in series on data, ~1000µF capacitor
  near the first LED (skippable for small bench tests, needed on the real
  16-LED build); brightness capped in software (USB current budget).
- **Color order confirmed via bench test: `NEO_RGB`, not the WS2812B-typical
  `NEO_GRB`** — tested on a bare 4-pin through-hole LED (legs, in order from
  the cut-corner side: DIN, VDD, GND, DOUT). Don't assume GRB when wiring the
  final build; verify per batch if the LED source changes.
- The original 100+ LED reel (WS2812B DC5V, confirmed via listing) did not
  light in testing (ruled out: wiring, continuity, resistor, pin, board
  health, timing frequency, color order — all checked). Root cause not yet
  confirmed, most likely a dead first LED in the chain. A bare spare LED
  wired the same way worked correctly, isolating the fault to the reel
  itself. Unresolved: either find a working segment further down the reel,
  or the reel needs replacing before the final 16-LED build.
- Pinout closed, 18/18 pins used, no spares.

### Case / component decisions (from a separate conversation, folded in 2026-07-21)
- **Switches**: Outemu, cheapest available, plate-mount (clip into 14mm
  square holes). Deliberately **not transparent** — lighting comes only from
  the LED strip/case diffusion, not through the switch itself.
- **Encoders**: EC11 with a **threaded bushing + nut** (not the bare/glue-mount
  kind) — this is the confirmed purchased variant. Because of this, the case
  Lid uses a simple **square anti-rotation recess**, not the earlier printed
  collar + retainer-clip mechanism (that approach is abandoned).
- **Keycaps**: DSA profile, PBT, bought in **both gray and white** (50pcs
  each). Whether this is intentional (e.g. a distinct color for the 2FX
  layer) or an accidental duplicate order is **unresolved** — don't assume
  either way, ask before designing around it.
- **Case screws**: M3 self-tapping, driven directly into printed pilot holes
  — no nuts or heat-set inserts anywhere except the encoders (which use their
  own nut for retention).
- **LED reconfirmed as WS2812B** (addressable), explicitly **not** a cheaper
  analog RGB strip — needed for the rainbow/per-LED effect, which an analog
  strip can't physically do. (This reverses an earlier cost-driven
  recommendation toward analog, from before the rainbow requirement came up.)

### Purchases / BOM (AliExpress, confirmed 2026-07-21)
Total paid: R$381,23 (coin/loyalty discount excluded from that figure).

| Item | Pack size | Qty bought |
|---|---|---|
| 1N4148 diodes | 100/pack | 2 packs (200 total) |
| Copper wire kit | 5×10m rolls | 1 kit (50m total) |
| EC11 rotary encoder (bushing+nut) | 5/pack | 2 packs (10 total) |
| Outemu switch, Brown | 70/pack | 1 pack |
| Keycap DSA, Gray | 50/pack | 1 pack |
| Keycap DSA, White | 50/pack | 1 pack |
| WS2812B LED strip | 2m / 120 LEDs | 1 |
| Arduino Pro Micro (USB-C) | 1/unit | 4 |

**User bought deliberately more than needed, for spares on future projects —
don't treat the surplus (diode count, encoder count, 4 Pro Micros, etc.) as a
mistake or suggest reducing it.**

### Firmware ↔ app protocol
- Firmware is "dumb": only reports raw events over serial (`BTN:5:DOWN`,
  `ENC:2:CW`, `ENC:2:PUSH`). The app decides actions.
- Exception: LED animation runs locally on the firmware (rainbow, breathing,
  1s touch flash, solid 2FX indicator) — timing is incompatible with a serial
  round-trip. The app only sends high-level config commands (e.g.
  "mode: rainbow").
- No on-device audio storage — explicitly decided against: no SD card, no
  USB Mass Storage. Sounds live in a folder on the PC.

### 2FX mode (second function / one-shot layer)
- Tapping the 2FX button arms layer 2. Configurable timeout in the app
  (default 10s, max 60s) — auto-disarms if no other button is pressed.
- A second tap on 2FX while armed cancels manually, no action executed.
- Any other button pressed while armed executes its layer-2 mapped action,
  then automatically returns to layer 1.
- This state logic (current layer, timeout, cancel) lives in the **app**, not
  the firmware. Already went through several refinement iterations — don't
  simplify without flagging it.

### Companion app (Python)
- GUI: PySide6 (Qt) — clickable visual 4x4 grid (`app.py`, project root).
  Per-key config popup: layer (1/2) + action type (`keyboard`, `macro`,
  `obs_scene`, `sound`, `empty`) + value. **`macro` type records a live key
  combo via `QKeySequenceEdit`** instead of typing it — same execution path
  as `keyboard` (both end up calling `pyautogui.hotkey`), only the input UX
  differs. Settings screen: just the 2FX timeout for now (label is in
  Portuguese: "Tempo de espera da segunda função (segundos)" — deliberate
  user choice, don't revert to English). Encoder config is a **separate
  dialog** ("Configure Encoders"), one row per encoder (1-3): a mode
  dropdown ("Volume Geral" = system / "Aplicativo" = per-app), and an
  app-picker (native file dialog filtered to `.exe`) that's only enabled in
  "Aplicativo" mode — writes `target: "system"` or `target: "app:<exe
  name>"` into config, matching the schema.
- **Python interpreter: must be a standalone python.org install, NOT
  Anaconda.** Discovered 2026-07-19 — `PySide6` fails to import under
  Anaconda's Python with `ImportError: DLL load failed while importing
  QtWidgets: The specified procedure could not be found`, even inside an
  isolated venv (venv doesn't isolate away from the base interpreter's
  DLL/PATH environment). This is a known, documented conflict — the Qt
  Project's own guidance is to avoid Anaconda for PySide6 projects. Fixed by
  installing a separate standalone Python (via `py install`, the
  `python.org` install manager) and recreating `.venv` from that interpreter
  instead (`py -V:3.14 -m venv .venv`). Anaconda itself was left untouched —
  this project's venv just now points at a different base interpreter.
- Serial: `pyserial`.
- Real per-process mute (Windows Core Audio API): `pycaw`.
- Audio playback: **`sounddevice`** (decided — supports targeting a specific
  output device per call, `pygame.mixer` doesn't; needed for routing sound
  effects into a call/stream, not just local playback). Needs `soundfile`
  alongside it for decoding. **Confirmed working**, routed a tone through
  VB-Cable's "CABLE Input" (WASAPI) and heard it via Windows' "Listen to this
  device" loopback on "CABLE Output." Gotcha: the WASAPI CABLE Input device
  requires **48000Hz** specifically (`PortAudioError: Invalid sample rate` at
  44100Hz) — check `sd.query_devices(index)['default_samplerate']` per
  device rather than assuming 44100.
- **Routing sound into OBS/streams: solved for free, nothing to build.** OBS
  28+'s built-in "Application Audio Capture" source grabs audio from a
  specific process directly — no virtual device needed, works automatically
  since Windows separates audio per-process.
- **Routing sound into Discord (or anything without OBS's capture feature):
  requires a virtual microphone driver — no way around it, Discord has no
  per-app capture equivalent.** Investigated whether one could be bundled
  into our own installer (2026-07-18):
  - VB-Audio VB-Cable: free for personal use, but commercial
    bundling/redistribution requires a paid, negotiated license directly
    with VB-Audio (not a flat fee).
  - `VirtualDrivers/Virtual-Audio-Driver` (GitHub, MIT-licensed, free to
    bundle) was tested as an embeddable alternative — **installed but failed
    with Code 52** ("Windows cannot verify the digital signature"), despite
    the release being labeled "Signed." Fix would be enabling Windows Test
    Signing Mode, which is disqualifying for a shipped product (desktop
    watermark, breaks other signed-driver/DRM/anti-cheat software
    system-wide) — not something we can ask customers to do. Driver was
    uninstalled; not currently viable.
  - **Current plan: use VB-Cable manually for our own dev/testing now.
    Revisit the paid VB-Audio distribution license (or re-test the MIT
    driver if it matures out of beta) once actually close to shipping** —
    this is a "before selling" decision, not a "Phase 9" one.
- OBS: `obsws-python` (obs-websocket v5, native since OBS 28) — direct scene
  command, not via OBS hotkeys.
- Simulating keyboard shortcuts: **`pyautogui`** (decided — no admin-rights
  requirement for a packaged `.exe`, unlike `keyboard`; confirmed working via
  config-driven test).
- Final packaging: PyInstaller → `.exe`.
- Mapping config saved locally (format likely JSON, not finalized), reloaded
  when the deck connects.

## Config file format (decided)
JSON, see `config.json` for a live sample. Shape: `settings.2fx_timeout_seconds`,
`buttons.<id>.layer1/layer2` (each `{type, value}`, types: `keyboard`,
`obs_scene`, `sound`, `empty`), `encoders.<id>.target` (`"system"` or
`"app:<processname>"`). Button 15 (2FX key) never appears in `buttons` — it's
the layer toggle, not a mappable action. Only configured buttons/encoders
need entries; missing = unmapped. Written/read by the GUI once it exists
(Phase 13) — hand-edited for now to test the loader.

## Hardware status (2026-07-19)
**Resolved — same Pro Micro recovered, no replacement needed.** Board
briefly failed USB enumeration ("Unknown USB Device (Device Descriptor
Request Failed)", `butterfly_recv` upload errors) after a wrong-processor-
setting upload attempt (3.3V/8MHz selected instead of the correct 5V/16MHz —
confirmed this couldn't have caused it, see below). Cable, port, and driver
reinstall were all ruled out as the cause. **Fix: the double-tap RST/GND
jumper reset has to happen *while the IDE is actively uploading* (right
after "Uploading..." appears), not before/while just plugging in** — timing
it that way is what finally got the bootloader to respond; earlier attempts
tapped reset at the wrong moment and looked identical to a dead board. If
this happens again, that's the fix to reach for first, before assuming
hardware failure.

Confirmed NOT caused by the wrong-processor-setting mix-up: normal sketch
uploads via the avr109 bootloader protocol cannot write fuse bits (the only
thing that could actually brick an AVR chip), and every upload attempt with
the wrong setting failed partway through anyway, so nothing was ever written
to the board from that.

Debounce fix for the button matrix (mirrors the encoder's debounce) is now
**verified on hardware** — re-uploaded and confirmed no more duplicate
`BTN:n:DOWN` events per press. Matrix, encoder, and LEDs all reconfirmed
working after the reconnection.

## Open decision — hardware-standalone operation (raised 2026-07-20, undecided)
User asked whether config could live on the hardware itself, app being "just
the door" to edit it, so the deck works without the PC app running. Honest
answer given: **partially possible, not fully — inherent limitation, not a
gap to fix.**
- **Can never run standalone** (need real OS/network access the Arduino
  doesn't have): sound playback/VB-Cable routing, OBS scene control,
  system/per-app volume+mute (`pycaw` needs Windows' own Core Audio API).
  Same reason Elgato Stream Deck/Loupedeck also require their own PC
  software running — not unique to this project.
- **Could move to hardware**: plain keyboard shortcuts only. Pro Micro's
  ATmega32U4 has native USB and can act as a real USB HID keyboard directly;
  mappings could be stored in its onboard EEPROM (written via the app over
  serial), letting those specific actions keep working even with the app
  fully closed/crashed (not just backgrounded).
- This is a real architecture change (rewrite firmware as native HID device
  + design EEPROM storage format) — not something to bolt on casually.
  **Undecided whether worth it, given the tray-icon fix (2026-07-20) already
  lets the app run invisibly in the background** — the EEPROM/HID approach
  only additionally helps if the app process isn't running at all. Revisit
  and decide in a future session; don't forget this was raised.

## Physical case design (OpenSCAD) — status as of 2026-07-22
Case design moved into **this** Claude Code session (user said the separate
claude.ai conversation's case decisions were wrong — case work now happens
here, in `case/`, not there). Tool: **OpenSCAD** (installed at
`E:\OpenScad\openscad.exe`, CLI-capable — used to render preview PNGs
directly via `openscad.exe -o out.png --camera=... --render file.scad`,
shown inline to the user for iteration, since neither `color()` nor the `%`
transparency modifier survive OpenSCAD's `--render` PNG export pipeline —
confirmed by direct testing, not just a hunch. For any future fit-check
that needs multiple distinguishable objects, the user's own OpenSCAD GUI
(F5 preview) is the reliable option, not a CLI screenshot.

**Design lineage:**
- Started from **MisteRdeck** (printables.com/model/134529, CC BY-SA,
  attribution: MattRigg) as loose visual inspiration only — no files used.
- User then provided a *different* reference actually downloaded to disk:
  **"DIY Mechanical Macro Keypad — Ocreeb"**
  (`D:\Downloads\DIY Mechanical Macro Keypad ― Ocreeb - 5535019\files\`,
  copied into `case/reference/`: `Case_Top.stl` [88×94×18mm, 4×3 keys + 2
  encoders], `Case_Bottom.stl` [86.5×92.5×10mm tray], `Knob.stl`). Confirmed
  with the user this is a **real derivative use** (not just inspiration) —
  CC BY-SA attribution + share-alike would apply to the case design
  specifically if it's ever shared/sold (electronics/firmware/app are
  unaffected).
- Tried scaling/stretching their actual STL non-uniformly — **don't do
  this**: it distorts fixed-angle chamfers unevenly. Abandoned in favor of
  fresh parametric geometry inspired by their style (chamfered corners +
  beveled top edge + recessed switch deck), which is what all `case_v*`
  files use now.

**Current real component count (do not confuse with the Ocreeb reference's
12 keys/2 encoders): 16 positions (4×4 incl. 2FX) + 3 encoders**, matching
the firmware/app. Layout: switch grid on the **left**, 3 encoders in a
column on the **right** (user's explicit call, reversing the Ocreeb
reference's top-mounted 2-encoder layout).

**Files** (in `case/`):
- `case_params.scad` — shared dimensions (switch pitch/hole, grid size,
  encoder spacing, margins, corner chamfer, `rim_height`=20mm, bevel,
  border, deck recess) — both top and bottom `include` this, keep them
  in sync through here, not by duplicating numbers.
- `case_v4_top.scad` — **current working file**, top plate. Contains
  `case_top()` (base: chamfered rim + tapered top bevel + recessed switch
  deck + 4×4 grid holes + 3 encoder holes, encoder hole `d=7mm` is a
  **placeholder — must be confirmed with calipers** before final print) and
  `case_top_split_tilt()` (the active top-level call — see "in-progress"
  below).
- `case_v4_bottom.scad` — bottom tray, slides up into the top's inner
  cavity from below. Has its own perimeter wall (not a flat disc — user
  explicitly asked for a wall so it slides/guides into the top, not just
  floats loose). `fit_clearance=0.25mm` per side (needed for FDM printing;
  an exact-match dimension won't physically slide).
- `case_v4_assembly.scad` — fit-check helper, `use`s both top and bottom.
- `case/reference/` — the Ocreeb STLs (unmodified, for visual reference /
  do-not-redistribute-without-attribution).
- `case/renders/*.png` — dated iteration screenshots, safe to ignore/delete,
  not load-bearing.

**Iteration history (what was tried and rejected, so it isn't retried):**
1. v1-v3: flat plate, various bevel attempts. v2's non-uniform-scaled-STL
   approach was rejected (see above). v3 fixed a real bug: OpenSCAD's
   `linear_extrude(scale=...)` scales around the **origin**, not the
   shape's center — an off-origin polygon bevels unevenly (2 sides get no
   taper at all) unless you center it before scaling and translate back
   after. Remember this if any future bevel/taper looks lopsided.
2. v4: added the recessed switch deck (hollow rim + separate deck slab —
   user wanted the keys visibly recessed below the outer bezel, matching
   the Ocreeb reference, not flush). Fixed `encoder_gap` 30→15 (user: too
   far from the keys). Increased `rim_height` 8→20mm (user: "2cm" walls).
   Bottom plate had a **real positioning bug**: it used `fit_clearance` as
   its offset instead of `border + fit_clearance`, so it sat near the
   outer corner instead of centered in the inner cavity — fixed.
3. v5 (abandoned): tried a single continuous slope (thin front, tall back)
   by slicing the whole shell with a rotated cutting plane. **This is
   wrong for this design** — it sliced straight through the switch deck
   and removed an entire row of keys, because the front height chosen was
   below the deck's Z-position. Any future "uniform slope" attempt must
   either keep front_height above the deck's top, or use the split-tilt
   approach below instead.
4. **v6 (current, in-progress, UNVERIFIED)**: user's actual request —
   left/right rails stay flat/vertical at the full `rim_height` (20mm, no
   angle at all); the *middle* section (the switch deck + all hole cutting)
   is tilted so its front (y=0) stays flush with the rails and its back
   (y=`plate_d`) sits `riser_height`=8mm higher. Implemented via
   **`multmatrix()` shear** (`case_top_split_tilt()`, current top-level
   call in `case_v4_top.scad`) — a shear repositions existing geometry
   instead of cutting into it, avoiding the v5 failure mode. Math was
   hand-verified but **never visually confirmed** — repeated attempts at
   finding a CLI camera angle that clearly shows the tilt profile failed
   (OpenSCAD's camera gimbal convention behaved inconsistently across
   attempts: same rx value gave a top-down view in one file and a side
   profile in another — don't trust remembered camera parameters, re-derive
   per file). **Next step when resuming: get the user to open this file in
   their own OpenSCAD GUI and confirm the tilt actually looks right — if
   not, the two things to adjust are `riser_height` and the shear math in
   `case_top_split_tilt()`.**

**Not yet built:** bottom tray hasn't been revisited since the split-tilt
change (may need its own wall-height adjustment to still mate correctly
with a tilted top — not checked yet). No STL has been exported for
printing yet — everything so far is still in the "getting the shape right"
iteration phase.

## Open items
- Physical case layout — see full status above. Components already
  purchased (see "Purchases / BOM").
- Whether the gray + white DSA keycap sets (50 each) are intentional (e.g.
  2FX layer color-coding) or a duplicate order — unresolved, ask before
  designing keycap layout around it.
- **Two-way serial protocol (PC → firmware LED commands, e.g. `LED:MODE:SOLID:RED`) deliberately deferred** — firmware currently only sends events, doesn't yet parse incoming commands. Must exist before Phase 14 (full integration), since that's how the app will drive LED behavior (including the 2FX indicator).
- **Discord audio routing driver decision (bundle vs. paid license vs. manual install) deferred to pre-launch** — see the "Routing sound into Discord" note above.

## Do NOT
- Assume automatic progression to the next step.
- Suggest SD card / on-device audio storage (explicitly decided against).
- Simplify the 2FX logic or the serial protocol without flagging it first.
