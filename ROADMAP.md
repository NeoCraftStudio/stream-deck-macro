# Roadmap

Each phase is a prerequisite for the next one, unless marked as a parallel
track. Status is updated manually as the project progresses.

```mermaid
flowchart TD
    S["Setup: Git + GitHub + Docs"]:::done --> P0["Phase 0: Hardware check"]:::current
    P0 --> P1["Phase 1: Firmware bring-up"]:::todo
    P1 --> P2["Phase 2: Button matrix"]:::todo
    P2 --> P3["Phase 3: Encoders"]:::todo
    P3 --> P4["Phase 4: WS2812B LEDs"]:::todo
    P4 --> P5["Phase 5: Merge + two-way protocol"]:::todo
    P5 --> P6["Phase 6: App serial reader"]:::todo
    P6 --> P7["Phase 7: Config format"]:::todo
    P7 --> P8["Phase 8: Keyboard shortcuts"]:::todo
    P8 --> P9["Phase 9: Audio playback"]:::todo
    P9 --> P10["Phase 10: OBS control"]:::todo
    P10 --> P11["Phase 11: Per-process mute"]:::todo
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
- [ ] Phase 0 — Hardware check (confirm Pro Micro voltage variant) **← current**
- [ ] Phase 1 — Firmware bring-up (toolchain, blink, serial hello world)
- [ ] Phase 2 — Firmware: button matrix scanning
- [ ] Phase 3 — Firmware: rotary encoders
- [ ] Phase 4 — Firmware: WS2812B LEDs
- [ ] Phase 5 — Firmware: merge + two-way serial protocol
- [ ] Phase 6 — App: serial reader (pyserial)
- [ ] Phase 7 — App: config file format (button → action mapping)
- [ ] Phase 8 — App: keyboard shortcut execution
- [ ] Phase 9 — App: audio playback
- [ ] Phase 10 — App: OBS control (obsws-python)
- [ ] Phase 11 — App: real per-process mute (pycaw)
- [ ] Phase 12 — App: 2FX layer state machine
- [ ] Phase 13 — App: GUI (PySide6)
- [ ] Phase 14 — Full integration (firmware + app, real hardware)
- [ ] Phase 15 — Packaging (PyInstaller .exe)
- [ ] Case — 3D-printed enclosure (parallel track, not blocking)
