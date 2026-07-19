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
- GUI: PySide6 (Qt) — clickable visual grid, per-key config popup
  (keyboard shortcut / OBS scene / sound file / empty), general settings
  screen (2FX timeout, encoder → app/audio-device mapping).
- Serial: `pyserial`.
- Real per-process mute (Windows Core Audio API): `pycaw`.
- Audio playback: **`sounddevice`** (decided — supports targeting a specific
  output device per call, `pygame.mixer` doesn't; needed for routing sound
  effects into a call/stream, not just local playback). Needs `soundfile`
  alongside it for decoding.
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

## Open items
- Physical case layout (researching 3D-printable models).
- **Two-way serial protocol (PC → firmware LED commands, e.g. `LED:MODE:SOLID:RED`) deliberately deferred** — firmware currently only sends events, doesn't yet parse incoming commands. Must exist before Phase 14 (full integration), since that's how the app will drive LED behavior (including the 2FX indicator).
- **Discord audio routing driver decision (bundle vs. paid license vs. manual install) deferred to pre-launch** — see the "Routing sound into Discord" note above.

## Do NOT
- Assume automatic progression to the next step.
- Suggest SD card / on-device audio storage (explicitly decided against).
- Simplify the 2FX logic or the serial protocol without flagging it first.
