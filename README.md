# Stream Deck Macro

DIY macro deck (Elgato Stream Deck style), built around an Arduino Pro Micro
(ATmega32U4): 4x4 button matrix with a secondary layer (2FX), 3 rotary
encoders for audio control, and individually addressable WS2812B LEDs per
key.

A companion Python app (PySide6) receives firmware events over serial and
executes the configured actions: keyboard shortcuts, OBS scene control, sound
playback, and real per-app mute.

## Status

Planning / study phase. Hardware architecture and protocol are already
defined; implementation hasn't started yet.

## Roadmap

```mermaid
flowchart TD
    S["Setup: Git + GitHub + Docs"]:::done --> P0["Phase 0: Hardware check"]:::done
    P0 --> P1["Phase 1: Firmware bring-up"]:::done
    P1 --> P2["Phase 2: Button matrix"]:::done
    P2 --> P3["Phase 3: Encoders"]:::done
    P3 --> P4["Phase 4: WS2812B LEDs"]:::done
    P4 --> P5["Phase 5: Merge + two-way protocol"]:::done
    P5 --> P6["Phase 6: App serial reader"]:::done
    P6 --> P7["Phase 7: Config format"]:::current
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

Full checklist with descriptions: [ROADMAP.md](ROADMAP.md)

## Learning project

This repository is also a learning exercise in Git, GitHub, and Python.
