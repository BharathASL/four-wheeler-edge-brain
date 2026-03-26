# Roadmap & Phases

This document summarizes the phased plan and suggested milestones.

Phase 0 — Parts & Setup
- Procurement checklist and environment requirements
- Draft Bill of Materials (BOM) for all required components
- Select motor HAT / driver board (e.g., Adafruit Motor HAT, L298N, MDD10A)
- Document power rail design (Pi power vs motor power separation)
- Document OS provisioning, headless Pi boot, SSH, and WiFi setup procedure

Note (initial analysis):
- This project will target Raspberry Pi 4 (4GB) for the initial analysis and Phase‑1 PoC.
- Use TinyLlama (quantized, GGML/llama.cpp) as the baseline on‑device model for testing memory and latency constraints.

Phase 1 — Edge Brain (PoC)
- Simulated loop: STT stub → Decision Engine → Action Executor → State
- Deliverables: move Phase‑1 documents into `docs/phase1/` folder, README, tests
- Remaining gaps: central config management, HTTP/REST API stub, conversation state machine

Phase 1.1 — Reliability & Safety Hardening (between Phase 1 and Phase 2)
- Unknown-command safe fallback (`ACTION:IDLE`) and confirmation flow
- Vosk/llama-cpp failure-mode handling and timeout policies
- Safety clamps, watchdog behavior, manual override, emergency stop policy
- Docs package: `docs/phase1_1/PHASE1_1.md`, `docs/phase1_1/ARCHITECTURE_TASKS.md`, `docs/phase1_1/SAFETY_AND_CONTROL.md`, `docs/phase1_1/FAILURE_MODES.md`
- Remaining gaps: STT failure degradation test, end-to-end integration test, failure-injection tests, input sanitization, rate limiting, log rotation policy, harness trend tracking

Phase 1.2 — Pi Hardware Bring-up (NEW — between Phase 1.1 and Phase 2)
- OS provisioning: flash 64-bit OS, configure hostname, user, SSH, and WiFi
- Run Pi validation script and record baseline latency/memory/temperature metrics
- Build and validate llama.cpp on ARM (complete TINYLLAMA_SETUP.md steps)
- Implement `src/motor_adapter.py` stub (real + mock, following adapter pattern)
- Wire up motors and verify GPIO/PWM signals with a basic spin test
- Docs: `docs/phase1_2/HARDWARE_BRINGUP.md`
- Exit criteria: inference running on device, motors responding to commands

Phase 2 — Basic Mobility
- Add hardware adapters for motor control and emergency stop
- Design GPIO/PWM duty cycle mapping and direction pin logic
- Define movement calibration procedure (speed balance, turn radius, deadband)
- Define simulation → hardware transition plan
- Decide on velocity PID control (closed-loop vs open-loop)
- Decide on wheel odometry / encoder feedback for distance estimation
- Hardware-in-loop testing plan

Phase 2.1 — Sensor Integration (NEW — between Phase 2 and Phase 3)
- Finalize sensor selection (ultrasonic vs 2D LiDAR, IMU model)
- Implement `src/sensor_adapter.py` (real + mock)
- Wire up sensors and validate live readings
- Feed real proximity readings into safety controller (replace simulation placeholders)
- IMU integration for orientation and tilt detection
- Define sensor fusion policy (weighted average, Kalman filter stub)
- Docs: `docs/phase2_1/SENSOR_INTEGRATION.md`

Phase 3 — Vision
- Camera integration and lightweight detection models
- Design vision processing pipeline: frame → pre-processing → inference → structured output
- Define vision-to-decision-engine integration schema
- Design frame streaming architecture (background thread, frame buffer, push events)
- Decide on object tracking strategy (per-frame only vs SORT/ByteTrack)
- Plan model export for Pi inference (ONNX / TFLite conversion)
- Draft vision data handling and privacy policy

Phase 4 — Audio Interface
- Offline STT/TTS integration
- Implement real Vosk STT decoder pipeline in audio adapter
- Define STT confidence threshold policy
- Design audio pre-processing (VAD, noise gate, AGC)
- Finalize TTS voice selection for production (Piper vs Coqui; pyttsx3 is dev-only)
- Plan/evaluate automatic speaker diarization

Phase 4.5 — Voice UX & Wake Word (NEW — between Phase 4 and Phase 5)
- Integrate wake-word engine (openWakeWord or Porcupine)
- Build conversation state machine: listening → processing → responding → idle
- Define STT confidence thresholds and rejection/fallback policy
- End-to-end voice test: wake word → STT → decision engine → TTS response

Phase 5 — Autonomous Navigation
- Obstacle avoidance and path planning
- Select path planning algorithm (reactive: VFH / potential fields, or deliberative: A*)
- Design sensor fusion architecture (ultrasonic + LiDAR + IMU)
- Plan waypoint / goal-based navigation system (named locations or coordinate map)
- Design recovery behaviors (stuck detection, recovery maneuvers)
- Define speed profile / acceleration ramp policy

Phase 6 — Mapping & Localization
- SLAM, mapping formats, ROS2 integration (optional)
- Draft ROS2 integration plan (or document explicit no-ROS decision)
- Design map persistence, versioning, and loading at startup
- Define loop closure policy
- Define initial pose / relocalization strategy after restart

Phase 7 — Docking & Self-Charging
- Dock detection, BMS integration
- Plan real BMS integration (I²C BMS or voltage divider for accurate battery state)
- Design dock alignment algorithm (visual servoing, IR beacon following, or dead-reckoning)
- Define charging verification logic (contact detection, current monitoring)
- Define docking safety policy (approach speed limits, abort conditions, re-attempt logic)

Phase 8 — Remote Management & Observability (NEW)
- Implement HTTP/REST API for remote command and state query
- Build simple web dashboard (status, battery, logs, last action)
- Add structured log shipping (optional: MQTT / local broker)
- Define OTA update strategy (git pull + venv refresh or package-based)
- Add health-check endpoint for external watchdog monitoring
- Document security model (API key, local network only, filesystem permissions)
