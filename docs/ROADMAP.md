# Roadmap & Phases

This document summarizes the phased plan and suggested milestones.

Phase 0 — Parts & Setup
- Procurement checklist and environment requirements

Note (initial analysis):
- This project will target Raspberry Pi 4 (4GB) for the initial analysis and Phase‑1 PoC.
- Use TinyLlama (quantized, GGML/llama.cpp) as the baseline on‑device model for testing memory and latency constraints.

Phase 1 — Edge Brain (PoC)
- Simulated loop: STT stub → Decision Engine → Action Executor → State
- Deliverables: move Phase‑1 documents into `docs/phase1/` folder, README, tests

Phase 1.1 — Safety Hardening (between Phase 1 and Phase 2)
- Unknown-command safe fallback (`ACTION:IDLE`) and confirmation flow
- Vosk/llama-cpp failure-mode handling and timeout policies
- Safety clamps, watchdog behavior, manual override, emergency stop policy
- Docs package: `docs/phase1_1/PHASE1_1.md`, `docs/phase1_1/ARCHITECTURE_TASKS.md`, `docs/phase1_1/SAFETY_AND_CONTROL.md`, `docs/phase1_1/FAILURE_MODES.md`

Phase 2 — Basic Mobility
- Add hardware adapters for motor control and emergency stop

Phase 3 — Vision
- Camera integration and lightweight detection models

Phase 4 — Audio Interface
- Offline STT/TTS integration

Phase 5 — Autonomous Navigation
- Obstacle avoidance and path planning

Phase 6 — Mapping & Localization
- SLAM, mapping formats, ROS2 integration (optional)

Phase 7 — Docking & Self-Charging
- Dock detection, BMS integration
