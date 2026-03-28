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
| **===== Phase 0 - Parts & Setup =====** |  |  |  |  |  |
| Decide optional sensors (ultrasonic vs 2D LiDAR, IMU) | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | Needed before nav/SLAM architecture freeze |
| Get docking components (charging contacts + marker: AprilTag or IR beacon) | Phase 0 - Parts & Setup | 🟡 To do | P1 | Hardware purchase | Needed for Phase 7 docking tests |
| Get USB microphone (Phase 1 testing) | Phase 0 - Parts & Setup | 🟡 To do | P2 | Hardware purchase | Needed for real STT testing |
| Get speaker (USB speaker or small amp + speaker) | Phase 0 - Parts & Setup | 🟡 To do | P2 | Hardware purchase | Needed for real TTS output |
| Get USB camera (Phase 3) | Phase 0 - Parts & Setup | 🟡 To do | P2 | Hardware purchase | Needed for live vision capture |
| Procure development compute (WSL-capable PC, Python 3.10+) | Phase 0 - Parts & Setup | ✅ Done (Implemented) | P1 | None | WSL development active |
| Add WSL bootstrap setup script for fresh dev machines | Phase 0 - Parts & Setup | ✅ Done (Implemented) | P1 | None | Added scripts/setup_wsl_dev.sh to install Ubuntu packages, create venv, and install repo deps |
| Procure target compute (Raspberry Pi + accessories) | Phase 0 - Parts & Setup | 🟡 To do | P1 | Hardware purchase | Planned for later |
| Draft Bill of Materials (BOM) for all required components | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | Single source of truth for procurement; create docs/phase0/BOM.md |
| Select and document motor HAT / driver board | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | e.g., Adafruit Motor HAT, L298N, MDD10A — decision gates Phase 1.2 motor wiring |
| Document power rail design (Pi power vs motor power separation) | Phase 0 - Parts & Setup | 🟡 To do | P1 | Motor HAT selection | Prevents brownout from motor current spikes on Pi 5V rail |
| Document OS provisioning and headless Pi boot procedure (flash, hostname, user, SSH, WiFi) | Phase 0 - Parts & Setup | 🟡 To do | P1 | None | Required before Phase 1.2 hardware bring-up; create docs/phase0/PI_SETUP.md |
| **===== Phase 1 - Edge Brain (PoC) =====** |  |  |  |  |  |
| Write minimal run instructions (README + scripts) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | README and validation scripts are present |
| Add output system (TTS + logs) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | pyttsx3 adapter + telemetry integrated |
| Add background tasks (battery drain + auto-dock trigger) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Background battery task integrated |
| Implement Action Executor (simulation) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Includes safety-aware handling |
| Implement Command -> Action mapping (contract) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Rules-first mappings documented and coded |
| Implement Decision Engine (rules + llama-cpp) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Uses llama adapter path with safe fallbacks |
| Implement State Manager (simulated robot state) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Thread-safe state and safety fields |
| Implement Input Listener (always-on loop) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Dedicated listener module added |
| Create Phase-1 PoC skeleton (simulated loop) | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P0 | None | Main simulation loop functional |
| Add central config management (src/config.py or config.yaml) | Phase 1 - Edge Brain (PoC) | ✅ Done | P1 | None | Consolidated scattered env-var constants into src/config.py (RobotConfig dataclass + from_env()) — PR: feature/phase1-central-config-management |
| Design HTTP/REST API stub for remote command and state query | Phase 1 - Edge Brain (PoC) | ✅ Done (Implemented) | P1 | None | Added local API stub with `/health`, `/state`, and `/command` endpoints, plus CLI/config wiring and test coverage (`feature/phase1-http-api-stub`) |
| Design conversation state machine for multi-step dialogues | Phase 1 - Edge Brain (PoC) | 🟡 To do | P2 | None | Enable goal sequences (go to kitchen → pick up → return) beyond one-shot commands |
| **===== Phase 1.1 - Reliability & Safety Hardening =====** |  |  |  |  |  |
| Add unknown-command confirmation flow (safe ACTION:IDLE) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Unknown commands now map to safe IDLE |
| Document Vosk failure modes + retries | Phase 1.1 - Reliability & Safety Hardening | 📝 Done (Documented) | P1 | None | Documented in phase1_1 failure modes doc |
| Document llama-cpp failure modes + timeouts | Phase 1.1 - Reliability & Safety Hardening | 📝 Done (Documented) | P1 | None | Documented in phase1_1 failure modes doc |
| Define max speed + proximity clamps | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Implemented in safety_controller |
| Add watchdog timers + manual override | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Watchdog task and override handling added |
| Define emergency stop behavior | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | ESTOP latch/reset implemented |
| Implement STT failure degradation to deterministic safe behavior | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Speech input listener now degrades STT failures to safe IDLE behavior with test coverage |
| Add end-to-end integration test (Input → Decision → Executor → State) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Added synchronous loop coverage around the runtime command-processing path |
| Refactor and harden chat behavior pipeline | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Chat behavior extracted to src/chat_behavior.py with deterministic routing, intent handling, and low-information fallback coverage |
| Improve chat-memory ranking and confidence scoring | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | SQLite + FTS path now ranks facts by overlap/direct match/recency and supports cleaner normalized recall for grounded memory answers |
| Harden grounded personal-memory responses and prompt-leak cleanup | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Cleanup now strips leaked prompt labels and rejects wrong-perspective personal-memory answers before user display |
| Add response perspective validation and raw-output cleanup | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Chat replies now sanitize prompt scaffolding, reject user-perspective leaks, and fall back to grounded responses when needed |
| Filter decision-engine model hints for user display | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Unknown-command model hints now reuse display-safe cleanup and fall back to a generic safe clarification message |
| Improve chat-memory conflict resolution and recency handling | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Fact extraction and retrieval now favor the latest matching user detail, and personal-fact statements are normalized before persistence so corrected facts stay cleaner across sessions |
| Add chat-memory regression coverage for contradiction and multi-session recall | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Regression tests now cover conflicting facts, leaked prompt scaffolding, cross-session alias recall, and per-user retrieval isolation |
| Add prompt/context compaction for chat memory injection | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Chat prompts now cap recent and retrieved turns so model context stays focused on high-signal memory snippets |
| Expand chat-memory evaluation coverage for paraphrase recall | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Migration-gate fixtures now include paraphrased memory queries with category-level recall reporting for direct vs paraphrase retrieval |
| Evaluate Qwen chat behavior and tighten the rule-vs-model boundary | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | Qwen local runtime available | Structured slots now cover exact-memory paths, while live Qwen validation confirms improved handling for open-ended explanation, reflective follow-up, advice, and short creative prompts without regressing exact memory guardrails |
| Add structured multi-fact memory extraction and typed slot storage | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | Qwen chat evaluation | Added typed slot extraction and persistence for multi-fact personal memory in `src/memory_slots.py` and `conversation_memory.py`, while keeping turn-level FTS/semantic fallback intact |
| Add deterministic correction and overwrite handling for remembered facts | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | Structured fact slots | Explicit correction language such as `Actually, change it to black` now updates the stored slot deterministically for exact recall |
| Separate session directives from durable personal memory | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | Structured fact slots | Response-style instructions such as `Always respond in one sentence.` are now detected as session directives and excluded from durable slot storage |
| Add typed compound-memory recall and transcript-based chat regressions | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | Structured fact slots | Added multi-slot recall, remembered-number storage, quoted multi-speaker rejection, and food/preference filtering regressions based on the Qwen transcript |
| Add rate limiting / cooldown on model calls | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Shared model cooldown guard now protects both command and chat paths and returns explicit cooldown responses instead of spamming model calls |
| Define and enforce log rotation / log file size policy | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Telemetry now uses rotating file handlers by default with env-configurable size and retention policy |
| Add input sanitization (guard against prompt injection) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | Shared prompt-input sanitizer now neutralizes role markers and special tokens before decision/chat model calls while preserving deterministic routing and stored history |
| Add harness trend tracking (historical accuracy + regression alerts) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | AI eval harness complete | AI evaluation harness now persists run history and surfaces regression alerts against previous runs |
| **===== Phase 2 - Mobility =====** |  |  |  |  |  |
| Wire brain <-> robot command interface (keep ACTION contract) | Phase 2 - Mobility | 🟡 To do | P0 | Hardware integration | Interface should preserve action schema |
| Implement physical movement system (forward/back/turn) | Phase 2 - Mobility | ⛔ Blocked (Hardware) | P0 | Motor hardware | Start after command interface is stable |
| Implement src/motor_adapter.py stub (real + mock, following adapter pattern) | Phase 2 - Mobility | ✅ Done (Implemented) | P0 | Motor HAT selection | Added `src/motor_adapter.py` with backend-facing PWM stub, deterministic mock adapter, executor integration, and focused motor/safety tests |
| Define GPIO/PWM duty cycle mapping and direction pin logic | Phase 2 - Mobility | 🟡 To do | P0 | Motor HAT selection | Translate speed_mps / angular_dps into PWM duty cycle and direction pins |
| Define movement calibration procedure (left/right balance, turn radius, deadband) | Phase 2 - Mobility | 🟡 To do | P1 | Motor hardware | Required for predictable movement; document calibration steps |
| Plan simulation → hardware transition (incremental PWM signal testing) | Phase 2 - Mobility | 🟡 To do | P1 | None | Draft step-by-step approach from mock state changes to real actuator output |
| Decide on velocity PID controller (closed-loop vs open-loop) | Phase 2 - Mobility | 🟡 To do | P1 | None | Open-loop drifts; decide whether encoder feedback is in Phase 2 scope |
| Decide on wheel odometry / encoder feedback for distance estimation | Phase 2 - Mobility | 🟡 To do | P2 | None | Required for accurate navigation in Phase 5; decide now to plan wiring |
| Define hardware-in-loop testing plan for motor commands | Phase 2 - Mobility | 🟡 To do | P1 | None | Test fixtures for command → motor output before full motion |
| **===== Phase 3 - Vision =====** |  |  |  |  |  |
| Set up live video capture (USB/Pi camera) | Phase 3 - Vision | ⛔ Blocked (Hardware) | P1 | Camera hardware | WSL can mock, real capture needs camera |
| Define target latency + FPS, document CPU/RAM constraints | Phase 3 - Vision | 🟡 To do | P1 | None | Can draft in WSL before hardware run |
| Select lightweight detector (YOLOv5-nano or MobileNet-SSD) | Phase 3 - Vision | 🟡 To do | P1 | None | Decision needed before integration |
| Design vision processing pipeline (frame → pre-processing → inference → structured output) | Phase 3 - Vision | 🟡 To do | P1 | Detector selection | Define end-to-end data flow before implementation |
| Define vision-to-decision-engine integration schema | Phase 3 - Vision | 🟡 To do | P1 | None | e.g., {detection: "person", distance_m: 1.2} → STOP; required contract |
| Design frame streaming architecture (background thread, frame buffer, event push) | Phase 3 - Vision | 🟡 To do | P1 | None | Decide threading model before implementing capture loop |
| Decide on object tracking strategy (per-frame only vs SORT/ByteTrack across frames) | Phase 3 - Vision | 🟡 To do | P2 | None | Tracking adds complexity; decide scope before implementation |
| Plan model export for Pi inference (ONNX / TFLite conversion from YOLOv5-nano) | Phase 3 - Vision | 🟡 To do | P1 | Detector selection | Export and quantize model for ARM inference on Pi |
| Draft vision data handling and privacy policy | Phase 3 - Vision | 🟡 To do | P2 | None | Indoor home robot captures video; document what is stored/transmitted |
| **===== Phase 4 - Audio =====** |  |  |  |  |  |
| Integrate offline STT (Vosk) with mic hardware | Phase 4 - Audio | ⛔ Blocked (Hardware) | P1 | Microphone hardware | Policy/docs done; runtime integration pending |
| Integrate offline TTS (Piper/Coqui) with speaker hardware | Phase 4 - Audio | ⛔ Blocked (Hardware) | P1 | Speaker hardware | pyttsx3 path exists for dev |
| Implement real Vosk STT decoder pipeline in audio_adapter.py | Phase 4 - Audio | ✅ Done (Implemented) | P1 | Microphone hardware | Added `VoskSpeechToTextAdapter` + `SoundDeviceAudioAdapter`, runtime STT mode wiring in `main.py`, config/env controls, and tests; verified WSL real mic capture and non-empty live transcript on 2026-03-28 (`feature/phase4-vosk-stt-pipeline`) |
| Define STT confidence threshold and rejection fallback policy | Phase 4 - Audio | 🟡 To do | P1 | None | Document minimum confidence score to act on; below threshold → re-prompt |
| Design audio pre-processing pipeline (VAD, noise gate, AGC) | Phase 4 - Audio | 🟡 To do | P1 | None | Improve STT accuracy before decoder; required for reliable voice UX |
| Finalize TTS voice selection for production (Piper vs Coqui; pyttsx3 is dev-only) | Phase 4 - Audio | 🟡 To do | P1 | None | Decide and document production TTS engine and voice model |
| Plan and evaluate automatic speaker diarization | Phase 4 - Audio | 🟡 To do | P2 | None | Current speaker ID is manual; evaluate whether auto diarization is in scope |
| **===== Phase 5 - Autonomous Navigation =====** |  |  |  |  |  |
| Implement obstacle avoidance logic (ultrasonic or LiDAR) | Phase 5 - Autonomous Navigation | ⛔ Blocked (Hardware) | P0 | Sensor selection + hardware | Depends on Phase 0 sensor decision |
| Select path planning algorithm (reactive: VFH/potential fields vs deliberative: A*) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | None | Decision gates navigation implementation; document trade-offs for Pi compute budget |
| Design sensor fusion architecture (ultrasonic + LiDAR + IMU data integration) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | Sensor integration (Phase 2.1) | Define fusion policy before implementing planner |
| Plan waypoint / goal-based navigation system (named locations or coordinate map) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | None | High-level goals require location abstraction above motion primitives |
| Design recovery behaviors (stuck detection and recovery maneuvers) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | None | Define stuck detection heuristics and escape maneuver sequences |
| Define speed profile / acceleration ramp policy (smooth start/stop) | Phase 5 - Autonomous Navigation | 🟡 To do | P1 | Motor adapter | Prevent wheel slip and tipping; ramp velocity rather than step change |
| **===== Phase 6 - SLAM / Mapping =====** |  |  |  |  |  |
| Define acceptable localization error | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Required for SLAM acceptance criteria |
| Specify map format (occupancy grid / ROS2 map) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Needed before stack integration |
| Choose SLAM stack (RTAB-Map or ORB-SLAM2) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | None | Align with compute budget |
| Draft ROS2 integration plan (or document explicit no-ROS decision) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | SLAM stack choice | Large architectural decision affecting entire stack; must be explicit |
| Design map persistence, versioning, and reload-at-startup strategy | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | Map format decision | Without persistence, robot must re-map on every boot |
| Define loop closure policy for SLAM (re-visiting known areas) | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | SLAM stack choice | Required for accurate long-session mapping |
| Define initial pose / relocalization strategy after restart | Phase 6 - SLAM / Mapping | 🟡 To do | P1 | Map persistence | How does robot locate itself on a previously built map after power cycle |
| **===== Phase 7 - Docking & Charging =====** |  |  |  |  |  |
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
| Design hybrid memory architecture (SQLite source-of-truth + FAISS semantic index) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | SemanticMemoryIndex with in-memory and FAISS-ready backends added; SQLite remains source of truth; runtime enablement gated on evaluator |
| Add semantic retrieval abstraction with FAISS-ready fallback path | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | src/semantic_memory.py implements SemanticMemoryIndex, HashingSemanticEncoder, InMemorySemanticBackend, and FaissSemanticBackend with safe fallback |
| Extend migration-gate evaluator for semantic and hybrid retrieval modes | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | evaluate_migration_gate.py now supports --retrieval-mode fts/semantic/hybrid and --semantic-backend flags with richer JSON report |
| Document semantic memory architecture and enablement gate | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P1 | None | docs/phase1/SEMANTIC_MEMORY_DESIGN.md captures design decisions, retrieval modes, encoder strategy, and the enablement gate criteria |
| Add AI evaluation harness (prompt set + expected action classes + report) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Added evaluator script with thresholded pass/fail and JSON report |
| Add failure-injection tests (timeout/model unavailable/malformed output) | Phase 1.1 - Reliability & Safety Hardening | ✅ Done (Implemented) | P0 | None | Decision engine tests now cover timeout, unavailable runtime, generic error, and malformed output |
| Evaluate semantic memory backend (FAISS/vector DB) for retrieval at scale | Phase 1.1 - Reliability & Safety Hardening | 🟡 To do | P2 | Migration gate complete | Consider once conversation volume grows beyond simple SQLite recall |
| Validate WSL development audio input path with Blue Yeti microphone | Bridge - WSL Dev Devices | ✅ Done (Implemented) | P1 | None | Validated on 2026-03-27 through WSLg Pulse `RDPSource`; Linux-side capture works and recorded spoken audio shows real signal levels, but the Blue Yeti is exposed generically through Windows audio routing rather than by device name |
| Validate WSL development audio output path through Windows speaker | Bridge - WSL Dev Devices | ✅ Done (Implemented) | P1 | None | Validated on 2026-03-27 in WSLg after installing ALSA/Pulse client packages and routing ALSA default output to Pulse; current pyttsx3/espeak-ng speech is audible but rough |
| Validate Android phone camera path for WSL development | Bridge - WSL Dev Devices | ✅ Done (Implemented) | P1 | None | Validated on 2026-03-27 using Android phone DroidCam network stream from WSL (`http://192.168.1.2:4747/video`) with successful one-frame capture to `/tmp/droidcam-test.jpg`; direct Android USBIP webcam streaming still unstable in this environment |
| Document approved WSL development-device workflow for mic, speaker, and camera | Bridge - WSL Dev Devices | ✅ Done (Implemented) | P1 | None | Approved development workflow documented: WSLg default-routed speaker + mic paths validated, and Android camera validated via DroidCam network stream fallback while USBIP webcam streaming remains optional/troubleshooting only |
| Run Pi bring-up validation and record latency/memory/temperature metrics | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | Use existing runbook and script |

## Phase 1.2 — Pi Hardware Bring-up

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Flash 64-bit OS and configure hostname, user, SSH, and WiFi | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | Follow docs/phase0/PI_SETUP.md once Pi arrives |
| Create docs/phase1_2/HARDWARE_BRINGUP.md (step-by-step bring-up guide) | Phase 1.2 - Pi Hardware Bring-up | 📝 Done (Documented) | P0 | None | Added practical bring-up guide with Pi setup, simulation-to-hardware sequence, validation checklist, and explicit hardware deferrals |
| Build and validate llama.cpp on ARM (complete TINYLLAMA_SETUP.md build steps) | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Raspberry Pi hardware | TINYLLAMA_SETUP.md has placeholder; fill in concrete ARM build commands |
| Implement src/motor_adapter.py stub (real + mock, following adapter pattern) | Phase 1.2 - Pi Hardware Bring-up | 🟡 To do | P0 | Motor HAT selection | Extend established adapter pattern; enables unit testing before hardware |
| Wire up motors and verify GPIO/PWM signals with basic spin test | Phase 1.2 - Pi Hardware Bring-up | ⛔ Blocked (Hardware) | P0 | Motor hardware + motor_adapter.py | First physical movement validation |
| Define Phase 1.2 exit criteria (inference running, motors responding to commands) | Phase 1.2 - Pi Hardware Bring-up | � Done (Documented) | P0 | None | Objective gates A–F (+ conditional motor gate) defined in `docs/phase1_2/HARDWARE_BRINGUP.md`; mapped to runbook tests and PASS/PARTIAL/FAIL outcome states in `docs/phase1/PI_VALIDATION_RUNBOOK.md`; gate summary block added to `scripts/phase1_validate_pi.sh` (`feature/phase1-2-exit-criteria`) |

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
| Implement HTTP/REST API for remote command and state query | Phase 8 - Remote Management | 🔵 In progress | P1 | None | Local Phase-1 stub is implemented; remaining work includes auth, service hardening, and broader remote-management surface |
| Build simple web dashboard (status, battery, logs, last action) | Phase 8 - Remote Management | 🟡 To do | P2 | HTTP API | Read-only dashboard for monitoring robot state remotely |
| Add structured log shipping (optional: MQTT / local broker) | Phase 8 - Remote Management | 🟡 To do | P2 | None | Central observability for multi-session debug |
| Define OTA update strategy (git pull + venv refresh or package-based) | Phase 8 - Remote Management | 🟡 To do | P1 | None | Required for updating firmware on deployed Pi without physical access |
| Add health-check endpoint for external watchdog monitoring | Phase 8 - Remote Management | 🟡 To do | P1 | HTTP API | Watchdog can restart service if health-check fails |
| Document security model (API key, local-network-only, filesystem permissions) | Phase 8 - Remote Management | 🟡 To do | P0 | HTTP API | Must not expose unauthenticated control interface on the network |

## Top Next Actions

1. ✅ Implement real Vosk STT decoder pipeline in `audio_adapter.py` (P1 — Phase 4 Audio) using the validated WSL dev input path.
2. 🟡 Define STT confidence threshold and rejection/re-prompt fallback policy (P1 — Phase 4 Audio).
3. 🟡 Design audio pre-processing pipeline (VAD, noise gate, AGC) for the input path (P1 — Phase 4 Audio).
4. 🟡 Finalize production TTS voice selection (Piper vs Coqui; pyttsx3 remains dev path) (P1 — Phase 4 Audio).
5. ⛔ Integrate offline STT (Vosk) with microphone hardware on Raspberry Pi when hardware path is ready (P1 — Phase 4 Audio).
6. ⛔ Integrate offline TTS (Piper/Coqui) with speaker hardware on Raspberry Pi when hardware path is ready (P1 — Phase 4 Audio).
7. 🟡 Build conversation state machine (listening -> processing -> responding -> idle) to support voice UX (P1 — Phase 4.5).
8. ⛔ Run end-to-end voice validation (wake word -> STT -> decision engine -> TTS) after audio hardware integration is complete (P0 — Phase 4.5).

## Infrastructure & Housekeeping

| Task | Phase | Status | Priority | Blocked By | Notes |
|---|---|---|---|---|---|
| Restructure src/ from flat layout into subpackages | Infrastructure | ✅ Done (Implemented) | P1 | None | Moved 18 modules into `src/adapters/`, `src/core/`, `src/memory/`, `src/api/`, `src/io/`; all imports updated; 175 tests passing (`feature/code-structure-cleanup`) |
| Remove accidentally committed research notes from repo root | Infrastructure | ✅ Done (Implemented) | P2 | None | Deleted `chaatgpt-report.md` and `gemini-response` from root; were never committed so removed from working tree |
| Remove .notices/ folder | Infrastructure | ✅ Done (Implemented) | P2 | None | Custom notice board folder removed; content tracked in `TASK_TRACKER.md` and `git log` instead |

---

Last updated: 2026-03-28 (Completed Phase 4 Vosk STT pipeline in WSL: decoder + real audio capture adapters, runtime wiring, config/CLI controls, automated tests, and live mic verification)
