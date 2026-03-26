# Project Task Tracker

This file is the source of truth for planning and progress tracking in the repository.

## Tracker Governance

- Always follow this tracker for planning and execution order.
- If plan, scope, phase, priority, or status changes, update this file in the same change.
- Do not close tasks in conversation-only updates; reflect status changes here first.
- Keep notes concise and action-oriented so the tracker remains readable.

## Status Legend

- 🟡 To do
- 🔵 In progress
- ✅ Done (Implemented)
- 📝 Done (Documented)
- ⛔ Blocked (Hardware)

## Priority Legend

- P0: Critical path
- P1: High priority
- P2: Nice-to-have / later

## Task Board

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Decide optional sensors (ultrasonic vs 2D LiDAR, IMU) | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | Needed before nav/SLAM architecture freeze |
| Get docking components (charging contacts + marker: AprilTag or IR beacon) | Phase 0 - Parts & Setup | 🟡 To do | P1 | Hardware purchase | Needed for Phase 7 docking tests |
| Get USB microphone (Phase 1 testing) | Phase 0 - Parts & Setup | 🟡 To do | P2 | Hardware purchase | Needed for real STT testing |
| Get speaker (USB speaker or small amp + speaker) | Phase 0 - Parts & Setup | 🟡 To do | P2 | Hardware purchase | Needed for real TTS output |
| Get USB camera (Phase 3) | Phase 0 - Parts & Setup | 🟡 To do | P2 | Hardware purchase | Needed for live vision capture |
| Procure development compute (WSL-capable PC, Python 3.10+) | Phase 0 - Parts & Setup | ✅ Done (Implemented) | P1 | None | WSL development active |
| Procure target compute (Raspberry Pi + accessories) | Phase 0 - Parts & Setup | 🟡 To do | P1 | Hardware purchase | Planned for later |
| Write minimal run instructions (README + scripts) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | README and validation scripts are present |
| Add output system (TTS + logs) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | pyttsx3 adapter + telemetry integrated |
| Add background tasks (battery drain + auto-dock trigger) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Background battery task integrated |
| Implement Action Executor (simulation) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Includes safety-aware handling |
| Implement Command -> Action mapping (contract) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Rules-first mappings documented and coded |
| Implement Decision Engine (rules + llama-cpp) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Uses llama adapter path with safe fallbacks |
| Implement State Manager (simulated robot state) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Thread-safe state and safety fields |
| Implement Input Listener (always-on loop) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Dedicated listener module added |
| Create Phase-1 PoC skeleton (simulated loop) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Main simulation loop functional |
| Add unknown-command confirmation flow (safe ACTION:IDLE) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Unknown commands now map to safe IDLE |
| Document Vosk failure modes + retries | Phase 1.1 - Reliability & Safety Hardening | 📝 Done (Documented) | P1 | None | Documented in phase1_1 failure modes doc |
| Document llama-cpp failure modes + timeouts | Phase 1.1 - Reliability & Safety Hardening | 📝 Done (Documented) | P1 | None | Documented in phase1_1 failure modes doc |
| Define max speed + proximity clamps | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Implemented in safety_controller |
| Add watchdog timers + manual override | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Watchdog task and override handling added |
| Define emergency stop behavior | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | ESTOP latch/reset implemented |
| Wire brain <-> robot command interface (keep ACTION contract) | Phase 2 - Mobility | 🟡 To do | P0 | Hardware integration | Interface should preserve action schema |
| Implement physical movement system (forward/back/turn) | Phase 2 - Mobility | ⛔ Blocked (Hardware) | P0 | Motor hardware | Start after command interface is stable |
| Set up live video capture (USB/Pi camera) | Phase 3 - Vision | ⛔ Blocked (Hardware) | P1 | Camera hardware | WSL can mock, real capture needs camera |
| Define target latency + FPS, document CPU/RAM constraints | Phase 3 - Vision | 🟡 To do | P1 | None | Can draft in WSL before hardware run |
| Select lightweight detector (YOLOv5-nano or MobileNet-SSD) | Phase 3 - Vision | 🟡 To do | P1 | None | Decision needed before integration |
| Integrate offline STT (Vosk) with mic hardware | Phase 4 - Audio | ⛔ Blocked (Hardware) | P1 | Microphone hardware | Policy/docs done; runtime integration pending |
| Integrate offline TTS (Piper/Coqui) with speaker hardware | Phase 4 - Audio | ⛔ Blocked (Hardware) | P1 | Speaker hardware | pyttsx3 path exists for dev |
| Implement obstacle avoidance logic (ultrasonic or LiDAR) | Phase 5 - Autonomous Navigation | ⛔ Blocked (Hardware) | P0 | Sensor selection + hardware | Depends on Phase 0 sensor decision |
| Define acceptable localization error | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Required for SLAM acceptance criteria |
| Specify map format (occupancy grid / ROS2 map) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Needed before stack integration |
| Choose SLAM stack (RTAB-Map or ORB-SLAM2) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Align with compute budget |
| Implement return-to-dock when battery low end-to-end | Phase 7 - Docking & Charging | ⛔ Blocked (Hardware) | P0 | Docking hardware | Simulation-only partial behavior exists |
| Implement dock detection (AprilTag / IR beacon / visual marker) | Phase 7 - Docking & Charging | ⛔ Blocked (Hardware) | P0 | Dock marker hardware | Depends on docking component choice |

## Bridge Tasks (Before Raspberry Pi Arrives)

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Add real-model mode switch (mock vs llama-cpp via env/flag) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Implemented in simulation runtime with env/CLI options |
| Add manual speaker identification flow for chat sessions | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Chat now prompts for speaker identity and supports profile switching |
| Add persistent per-speaker conversation memory (SQLite) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Per-speaker turns are stored and reused for contextual answers |
| Add SQLite FTS retrieval for long-history recall | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Retrieve relevant older turns without loading full history into prompt |
| Add retrieval benchmark hooks for migration-gate metrics | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Latency and retrieval-hit hooks added for recall benchmarking |
| Define objective migration gate (latency + recall metrics) for FAISS adoption | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Evaluator script records recall@k and latency percentiles with threshold decision |
| Design hybrid memory architecture (SQLite source-of-truth + FAISS semantic index) | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P1 | Migration gate complete | Keep metadata/filtering in SQLite; use FAISS for semantic nearest-neighbor |
| Add AI evaluation harness (prompt set + expected action classes + report) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Added evaluator script with thresholded pass/fail and JSON report |
| Add failure-injection tests (timeout/model unavailable/malformed output) | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P0 | None | Improves reliability confidence |
| Evaluate semantic memory backend (FAISS/vector DB) for retrieval at scale | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P2 | Migration gate complete | Consider once conversation volume grows beyond simple SQLite recall |
| Run Pi bring-up validation and record latency/memory/temperature metrics | Phase 1.1 - Reliability & Safety Hardening | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | Use existing runbook and script |

## Top 10 Next Actions

1. 🟡 Add failure-injection tests for model timeout/unavailable/malformed outputs.
2. 🟡 Validate migration-gate thresholds with retrieval benchmark data across long conversations.
3. 🟡 Finalize sensor choice (ultrasonic vs 2D LiDAR, IMU).
4. 🟡 Decide and document vision detector baseline and performance targets.
5. 🟡 Draft command-interface spec for brain <-> robot mobility bridge.
6. 🟡 Procure Raspberry Pi target compute and docking components.
7. 🟡 Procure microphone, speaker, and camera for hardware integration.
8. ⛔ Run Pi validation script and record baseline runtime metrics once hardware arrives.
9. 🟡 Draft FAISS hybrid migration plan once gate thresholds fail consistently.
10. 🟡 Add harness trend tracking (historical accuracy and regression alerts).

---

Last updated: 2026-03-26
