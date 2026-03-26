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
| Draft Bill of Materials (BOM) for all required components | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | Single source of truth for procurement; create docs/phase0/BOM.md |
| Select and document motor HAT / driver board | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | e.g., Adafruit Motor HAT, L298N, MDD10A — decision gates Phase 1.2 motor wiring |
| Document power rail design (Pi power vs motor power separation) | Phase 0 - Parts & Setup | 🟡 To do | P1 | Motor HAT selection | Prevents brownout from motor current spikes on Pi 5V rail |
| Document OS provisioning and headless Pi boot procedure (flash, hostname, user, SSH, WiFi) | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | Required before Phase 1.2 hardware bring-up; create docs/phase0/PI_SETUP.md |
| Write minimal run instructions (README + scripts) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | README and validation scripts are present |
| Add output system (TTS + logs) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | pyttsx3 adapter + telemetry integrated |
| Add background tasks (battery drain + auto-dock trigger) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Background battery task integrated |
| Implement Action Executor (simulation) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Includes safety-aware handling |
| Implement Command -> Action mapping (contract) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Rules-first mappings documented and coded |
| Implement Decision Engine (rules + llama-cpp) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Uses llama adapter path with safe fallbacks |
| Implement State Manager (simulated robot state) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Thread-safe state and safety fields |
| Implement Input Listener (always-on loop) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Dedicated listener module added |
| Create Phase-1 PoC skeleton (simulated loop) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Main simulation loop functional |
| Add central config management (src/config.py or config.yaml) | Phase 1 - Edge Brain (PoC) | 🟡 To do | P1 | None | Consolidate scattered env-var constants (speeds, timeouts, depths) into one place |
| Design HTTP/REST API stub for remote command and state query | Phase 1 - Edge Brain (PoC) | 🟡 To do | P1 | None | Architecture doc calls for it; required for Phase 8 remote management |
| Design conversation state machine for multi-step dialogues | Phase 1 - Edge Brain (PoC) | 🟡 To do | P2 | None | Enable goal sequences (go to kitchen → pick up → return) beyond one-shot commands |
| Add unknown-command confirmation flow (safe ACTION:IDLE) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Unknown commands now map to safe IDLE |
| Document Vosk failure modes + retries | Phase 1.1 - Reliability & Safety Hardening | 📝 Done (Documented) | P1 | None | Documented in phase1_1 failure modes doc |
| Document llama-cpp failure modes + timeouts | Phase 1.1 - Reliability & Safety Hardening | 📝 Done (Documented) | P1 | None | Documented in phase1_1 failure modes doc |
| Define max speed + proximity clamps | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Implemented in safety_controller |
| Add watchdog timers + manual override | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Watchdog task and override handling added |
| Define emergency stop behavior | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | ESTOP latch/reset implemented |
| Implement STT failure degradation to deterministic safe behavior | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P0 | None | Validation checklist item unchecked; add Vosk failure path and test coverage |
| Add end-to-end integration test (Input → Decision → Executor → State) | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P0 | None | No full-loop test exists; unit tests cover modules in isolation only |
| Add rate limiting / cooldown on model calls | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P1 | None | Prevent model spam on rapid input; implement debounce or queue limit |
| Define and enforce log rotation / log file size policy | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P1 | None | Telemetry logs without rotation; add RotatingFileHandler or logrotate config |
| Add input sanitization (guard against prompt injection) | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P1 | None | User input passed directly to model prompt; strip/escape dangerous patterns |
| Add harness trend tracking (historical accuracy + regression alerts) | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P1 | AI eval harness complete | Persist baseline metrics; alert on accuracy regression across runs |
| Wire brain <-> robot command interface (keep ACTION contract) | Phase 2 - Mobility | 🟡 To do | P0 | Hardware integration | Interface should preserve action schema |
| Implement physical movement system (forward/back/turn) | Phase 2 - Mobility | ⛔ Blocked (Hardware) | P0 | Motor hardware | Start after command interface is stable |
| Implement src/motor_adapter.py stub (real + mock, following adapter pattern) | Phase 2 - Mobility | 🟡 To do | P0 | Motor HAT selection | Extend established adapter pattern; GPIO/PWM backend + mock for tests |
| Define GPIO/PWM duty cycle mapping and direction pin logic | Phase 2 - Mobility | 🟡 To do | P0 | Motor HAT selection | Translate speed_mps / angular_dps into PWM duty cycle and direction pins |
| Define movement calibration procedure (left/right balance, turn radius, deadband) | Phase 2 - Mobility | 🟡 To do | P1 | Motor hardware | Required for predictable movement; document calibration steps |
| Plan simulation → hardware transition (incremental PWM signal testing) | Phase 2 - Mobility | 🟡 To do | P1 | None | Draft step-by-step approach from mock state changes to real actuator output |
| Decide on velocity PID controller (closed-loop vs open-loop) | Phase 2 - Mobility | 🟡 To do | P1 | None | Open-loop drifts; decide whether encoder feedback is in Phase 2 scope |
| Decide on wheel odometry / encoder feedback for distance estimation | Phase 2 - Mobility | 🟡 To do | P2 | None | Required for accurate navigation in Phase 5; decide now to plan wiring |
| Define hardware-in-loop testing plan for motor commands | Phase 2 - Mobility | 🟡 To do | P1 | None | Test fixtures for command → motor output before full motion |
| Set up live video capture (USB/Pi camera) | Phase 3 - Vision | ⛔ Blocked (Hardware) | P1 | Camera hardware | WSL can mock, real capture needs camera |
| Define target latency + FPS, document CPU/RAM constraints | Phase 3 - Vision | 🟡 To do | P1 | None | Can draft in WSL before hardware run |
| Select lightweight detector (YOLOv5-nano or MobileNet-SSD) | Phase 3 - Vision | 🟡 To do | P1 | None | Decision needed before integration |
| Design vision processing pipeline (frame → pre-processing → inference → structured output) | Phase 3 - Vision | 🟡 To do | P1 | Detector selection | Define end-to-end data flow before implementation |
| Define vision-to-decision-engine integration schema | Phase 3 - Vision | 🟡 To do | P1 | None | e.g., {detection: "person", distance_m: 1.2} → STOP; required contract |
| Design frame streaming architecture (background thread, frame buffer, event push) | Phase 3 - Vision | 🟡 To do | P1 | None | Decide threading model before implementing capture loop |
| Decide on object tracking strategy (per-frame only vs SORT/ByteTrack across frames) | Phase 3 - Vision | 🟡 To do | P2 | None | Tracking adds complexity; decide scope before implementation |
| Plan model export for Pi inference (ONNX / TFLite conversion from YOLOv5-nano) | Phase 3 - Vision | 🟡 To do | P1 | Detector selection | Export and quantize model for ARM inference on Pi |
| Draft vision data handling and privacy policy | Phase 3 - Vision | 🟡 To do | P2 | None | Indoor home robot captures video; document what is stored/transmitted |
| Integrate offline STT (Vosk) with mic hardware | Phase 4 - Audio | ⛔ Blocked (Hardware) | P1 | Microphone hardware | Policy/docs done; runtime integration pending |
| Integrate offline TTS (Piper/Coqui) with speaker hardware | Phase 4 - Audio | ⛔ Blocked (Hardware) | P1 | Speaker hardware | pyttsx3 path exists for dev |
| Implement real Vosk STT decoder pipeline in audio_adapter.py | Phase 4 - Audio | 🟡 To do | P1 | Microphone hardware | Only a stub exists; implement full Vosk decode + retry logic |
| Define STT confidence threshold and rejection fallback policy | Phase 4 - Audio | 🟡 To do | P1 | None | Document minimum confidence score to act on; below threshold → re-prompt |
| Design audio pre-processing pipeline (VAD, noise gate, AGC) | Phase 4 - Audio | 🟡 To do | P1 | None | Improve STT accuracy before decoder; required for reliable voice UX |
| Finalize TTS voice selection for production (Piper vs Coqui; pyttsx3 is dev-only) | Phase 4 - Audio | 🟡 To do | P1 | None | Decide and document production TTS engine and voice model |
| Plan and evaluate automatic speaker diarization | Phase 4 - Audio | 🟡 To do | P2 | None | Current speaker ID is manual; evaluate whether auto diarization is in scope |
| Implement obstacle avoidance logic (ultrasonic or LiDAR) | Phase 5 - Autonomous Navigation | ⛔ Blocked (Hardware) | P0 | Sensor selection + hardware | Depends on Phase 0 sensor decision |
| Select path planning algorithm (reactive: VFH/potential fields vs deliberative: A*) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | None | Decision gates navigation implementation; document trade-offs for Pi compute budget |
| Design sensor fusion architecture (ultrasonic + LiDAR + IMU data integration) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | Sensor integration (Phase 2.1) | Define fusion policy before implementing planner |
| Plan waypoint / goal-based navigation system (named locations or coordinate map) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | None | High-level goals require location abstraction above motion primitives |
| Design recovery behaviors (stuck detection and recovery maneuvers) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | None | Define stuck detection heuristics and escape maneuver sequences |
| Define speed profile / acceleration ramp policy (smooth start/stop) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | Motor adapter | Prevent wheel slip and tipping; ramp velocity rather than step change |
| Define acceptable localization error | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Required for SLAM acceptance criteria |
| Specify map format (occupancy grid / ROS2 map) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Needed before stack integration |
| Choose SLAM stack (RTAB-Map or ORB-SLAM2) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Align with compute budget |
| Draft ROS2 integration plan (or document explicit no-ROS decision) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | SLAM stack choice | Large architectural decision affecting entire stack; must be explicit |
| Design map persistence, versioning, and reload-at-startup strategy | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | Map format decision | Without persistence, robot must re-map on every boot |
| Define loop closure policy for SLAM (re-visiting known areas) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | SLAM stack choice | Required for accurate long-session mapping |
| Define initial pose / relocalization strategy after restart | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | Map persistence | How does robot locate itself on a previously built map after power cycle |
| Implement return-to-dock when battery low end-to-end | Phase 7 - Docking & Charging | ⛔ Blocked (Hardware) | P0 | Docking hardware | Simulation-only partial behavior exists |
| Implement dock detection (AprilTag / IR beacon / visual marker) | Phase 7 - Docking & Charging | ⛔ Blocked (Hardware) | P0 | Dock marker hardware | Depends on docking component choice |
| Plan real BMS integration (I²C BMS or voltage divider for accurate battery state) | Phase 7 - Docking & Charging | 🟡 To do | P1 | None | Simulation uses fake percentage; real integration needs hardware-level monitoring |
| Design dock alignment algorithm (visual servoing, IR beacon following, or dead-reckoning) | Phase 7 - Docking & Charging | 🟡 To do | P1 | Dock detection implementation | Precise contact alignment requires dedicated control loop |
| Define charging verification logic (contact detection, current monitoring) | Phase 7 - Docking & Charging | 🟡 To do | P1 | BMS integration | Software must confirm charging has started and detect completion |
| Define docking safety policy (approach speed limits, abort conditions, re-attempt logic) | Phase 7 - Docking & Charging | 🟡 To do | P1 | None | Prevent damage from misaligned docking attempts |

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
| Run Pi bring-up validation and record latency/memory/temperature metrics | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | Use existing runbook and script |

## Phase 1.2 — Pi Hardware Bring-up

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Flash 64-bit OS and configure hostname, user, SSH, and WiFi | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | Follow docs/phase0/PI_SETUP.md once Pi arrives |
| Create docs/phase1_2/HARDWARE_BRINGUP.md (step-by-step bring-up guide) | Phase 1.2 - Pi Hardware Bring-up | 🟡 To do | P0 | None | Can draft now; fillable checklist for when Pi arrives |
| Build and validate llama.cpp on ARM (complete TINYLLAMA_SETUP.md build steps) | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | TINYLLAMA_SETUP.md has placeholder; fill in concrete ARM build commands |
| Implement src/motor_adapter.py stub (real + mock, following adapter pattern) | Phase 1.2 - Pi Hardware Bring-up | 🟡 To do | P0 | Motor HAT selection | Extend established adapter pattern; enables unit testing before hardware |
| Wire up motors and verify GPIO/PWM signals with basic spin test | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Motor hardware + motor_adapter.py | First physical movement validation |
| Define Phase 1.2 exit criteria (inference running, motors responding to commands) | Phase 1.2 - Pi Hardware Bring-up | 🟡 To do | P0 | None | Written acceptance criteria needed before phase can be closed |

## Phase 2.1 — Sensor Integration

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Finalize sensor selection (ultrasonic vs 2D LiDAR, IMU model) | Phase 2.1 - Sensor Integration | 🟡 To do | P0 | None | Unblocks sensor adapter design and Phase 5 nav architecture |
| Implement src/sensor_adapter.py (real + mock, following adapter pattern) | Phase 2.1 - Sensor Integration | 🟡 To do | P1 | Sensor selection | Extend adapter pattern; mock enables testing before hardware |
| Wire up sensors and validate live readings on Pi | Phase 2.1 - Sensor Integration | ⛔ Blocked (Hardware) | P1 | Sensor hardware + sensor_adapter.py | Verify I²C / GPIO readings match expected values |
| Feed real proximity readings into safety controller (replace simulation placeholders) | Phase 2.1 - Sensor Integration | ⛔ Blocked (Hardware) | P0 | Sensor hardware | MIN_FRONT_PROXIMITY_M clamp currently uses simulated values |
| IMU integration for orientation and tilt detection | Phase 2.1 - Sensor Integration | ⛔ Blocked (Hardware) | P1 | IMU hardware | Enables tilt-safety cutoff and future nav orientation |
| Define sensor fusion policy (weighted average, Kalman filter stub) | Phase 2.1 - Sensor Integration | 🟡 To do | P1 | Sensor selection | Required before integrating multiple sensors into one proximity estimate |
| Create docs/phase2_1/SENSOR_INTEGRATION.md | Phase 2.1 - Sensor Integration | 🟡 To do | P1 | Sensor selection | Document wiring, driver libraries, and data format |

## Phase 4.5 — Voice UX & Wake Word

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Integrate wake-word engine (openWakeWord or Porcupine) | Phase 4.5 - Voice UX & Wake Word | ⛔ Blocked (Hardware) | P1 | Microphone hardware | Required for hands-free always-on UX |
| Build conversation state machine (listening → processing → responding → idle) | Phase 4.5 - Voice UX & Wake Word | 🟡 To do | P1 | None | Can design state machine now; implement once STT hardware is available |
| Define STT confidence thresholds and rejection/re-prompt fallback policy | Phase 4.5 - Voice UX & Wake Word | 🟡 To do | P1 | None | Document minimum acceptable confidence score for acting on STT output |
| Add audio pre-processing (VAD, noise gate) to input pipeline | Phase 4.5 - Voice UX & Wake Word | ⛔ Blocked (Hardware) | P1 | Microphone hardware | Improves STT accuracy in noisy environments |
| End-to-end voice test: wake word → STT → decision engine → TTS response | Phase 4.5 - Voice UX & Wake Word | ⛔ Blocked (Hardware) | P0 | All audio hardware | Phase 4.5 exit criteria validation test |

## Phase 8 — Remote Management & Observability

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Implement HTTP/REST API for remote command and state query | Phase 8 - Remote Management | 🟡 To do | P1 | None | Architecture doc specifies CLI / HTTP API; required for remote operation |
| Build simple web dashboard (status, battery, logs, last action) | Phase 8 - Remote Management | 🟡 To do | P2 | HTTP API | Read-only dashboard for monitoring robot state remotely |
| Add structured log shipping (optional: MQTT / local broker) | Phase 8 - Remote Management | 🟡 To do | P2 | None | Central observability for multi-session debug |
| Define OTA update strategy (git pull + venv refresh or package-based) | Phase 8 - Remote Management | 🟡 To do | P1 | None | Required for updating firmware on deployed Pi without physical access |
| Add health-check endpoint for external watchdog monitoring | Phase 8 - Remote Management | 🟡 To do | P1 | HTTP API | Watchdog can restart service if health-check fails |
| Document security model (API key, local-network-only, filesystem permissions) | Phase 8 - Remote Management | 🟡 To do | P0 | HTTP API | Must not expose unauthenticated control interface on the network |

## Top 10 Next Actions

1. 🟡 Add failure-injection tests for model timeout/unavailable/malformed outputs (P0 — Phase 1.1).
2. 🟡 Implement STT failure degradation to deterministic safe behavior and add test coverage (P0 — Phase 1.1 validation gap).
3. 🟡 Add end-to-end integration test covering full Input → Decision → Executor → State loop (P0 — Phase 1.1).
4. 🟡 Implement src/motor_adapter.py stub (real + mock) to extend the adapter pattern before hardware arrives (P0 — Phase 1.2).
5. 🟡 Draft docs/phase1_2/HARDWARE_BRINGUP.md bring-up guide (can be done now, before Pi arrives) (P0 — Phase 1.2).
6. 🟡 Add central config management (src/config.py or config.yaml) to consolidate scattered constants (P1 — Phase 1).
7. 🟡 Finalize sensor choice (ultrasonic vs 2D LiDAR, IMU) to unblock Phase 2.1 and Phase 5 architecture (P0 — Phase 2.1).
8. 🟡 Draft command-interface spec for brain <-> robot mobility bridge (P0 — Phase 2).
9. 🟡 Validate migration-gate thresholds with retrieval benchmark data across long conversations (P1 — Phase 1.1).
10. ⛔ Procure Raspberry Pi, motor HAT, microphone, speaker, camera, and docking components (P1 — Phase 0).

---

Last updated: 2026-03-26 (gap analysis — added Phase 1.2, Phase 2.1, Phase 4.5, Phase 8 and 40+ missing tasks across all phases)
