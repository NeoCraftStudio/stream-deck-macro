# Roadmap

Each phase is a prerequisite for the next one, unless marked as a parallel
track. Status is updated manually as the project progresses.

```mermaid
flowchart TD
    S["Setup: Git + GitHub + Docs"]:::done --> P0["Phase 0: Hardware check"]:::done
    P0 --> P1["Phase 1: Firmware bring-up"]:::done
    P1 --> P2["Phase 2: Button matrix"]:::done
    P2 --> P3["Phase 3: Encoders"]:::done
    P3 --> P4["Phase 4: WS2812B LEDs"]:::done
    P4 --> P5["Phase 5: Merge + two-way protocol"]:::done
    P5 --> P6["Phase 6: App serial reader"]:::done
    P6 --> P7["Phase 7: Config format"]:::done
    P7 --> P8["Phase 8: Keyboard shortcuts"]:::done
    P8 --> P9["Phase 9: Audio playback"]:::done
    P9 --> P10["Phase 10: OBS control"]:::done
    P10 --> P11["Phase 11: Per-process mute"]:::current
    P11 --> P12["Phase 12: 2FX state machine"]:::todo
    P12 --> P13["Phase 13: GUI (PySide6)"]:::todo
    P13 --> P14["Phase 14: Full integration"]:::todo
    P14 --> P15["Phase 15: Packaging .exe"]:::todo
    P0 -.-> C["Case: 3D-printed enclosure"]:::todo
    C -.-> P14

    classDef done fill:#2ea043,stroke:#2ea043,color:#fff
    classDef current fill:#d29922,stroke:#d29922,color:#000
    classDef todo fill:#30363d,stroke:#8b949e,color:#c9d1d9
```

🟢 done · 🟡 current · ⬛ not started

## Checklist

- [x] Setup — Git, GitHub repo, README, LICENSE, .gitignore, CLAUDE.md
- [x] Phase 0 — Hardware check (confirmed: Pro Micro 5V / 16MHz variant, no level shifter needed)
- [x] Phase 1 — Firmware bring-up (toolchain, blink, serial hello world)
- [x] Phase 2 — Firmware: button matrix scanning (all 16 positions confirmed)
- [x] Phase 3 — Firmware: rotary encoders (CW/CCW/PUSH logic verified on 1 of 3 encoders; other 2 are only repeats of the same wiring, to be confirmed when in hand)
- [x] Phase 4 — Firmware: WS2812B LEDs (chaining + color order confirmed on 9 spare bare LEDs; original 100+ LED reel is faulty, unresolved — see CLAUDE.md)
- [x] Phase 5 — Firmware: merge (matrix + encoder + LEDs, one sketch) done; **two-way protocol (PC→firmware LED commands) deliberately deferred** — revisit before Phase 14
- [x] Phase 6 — App: serial reader (pyserial), confirmed reading BTN/ENC events live
- [x] Phase 7 — App: config file format (JSON schema designed, `config.json` sample + loader confirmed working)
- [x] Phase 8 — App: keyboard shortcut execution (`pyautogui`, confirmed via config-driven `ctrl+c` test)
- [x] Phase 9 — App: audio playback (`sounddevice`, confirmed routing through VB-Cable to a specific device)
- [x] Phase 10 — App: OBS control (`obsws-python`, confirmed scene switch)
- [ ] Phase 11 — App: real per-process mute (pycaw) **← current**
- [ ] Phase 12 — App: 2FX layer state machine
- [ ] Phase 13 — App: GUI (PySide6)
- [ ] Phase 14 — Full integration (firmware + app, real hardware)
- [ ] Phase 15 — Packaging (PyInstaller .exe)
- [ ] Case — 3D-printed enclosure (parallel track, not blocking)
