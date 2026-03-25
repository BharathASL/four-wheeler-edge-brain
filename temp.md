# Autonomous 4-Wheeler Home Robot (Offline AI) – Phased Plan

## 🎯 Goal

Build a low-cost, fully offline autonomous robot that:

* Moves on 4 wheels
* Recharges itself using a docking station
* Sees using a camera
* Listens and speaks (voice interface)
* Maps the house and finds safe resting spots
* Detects events (noise/motion) and records

---

# 🤖 Robot Capabilities (Functional Scope)

### 🧠 Core Intelligence

* Understand voice commands (offline)
* Maintain internal state (battery, location, tasks)
* Make decisions based on rules + AI
* Respond with speech

### 🔋 Power & Self-Maintenance

* Monitor battery level continuously
* Auto-decide when to go to dock
* Simulate/perform charging cycle
* Resume tasks after charging

### 🎧 Audio Awareness

* Always-on listening loop
* Detect trigger words / commands
* Detect unusual sounds (future)
* Move toward sound source (future)

### 👁️ Vision (Phase 3+)

* Capture live video feed
* Detect people / obstacles
* Detect motion and start recording
* Recognize known zones (future)

### 🗺️ Navigation & Movement (Phase 2+)

* Move in directions (forward/back/turn)
* Avoid obstacles
* Navigate to target locations
* Return to dock autonomously

### 🏠 Environment Understanding (Phase 6+)

* Build map of house (SLAM)
* Identify safe resting zones
* Track current position

### 📹 Monitoring & Security

* Record video on motion detection
* Respond to noise events
* Log important events

### 🧩 Behavior System

* Idle when no task
* Interrupt current task on priority events
* Multi-condition decisions (battery + command + environment)

### 🔌 Integration Ready

* Output structured ACTION commands
* Plug into hardware without changing logic
* Support future modules (sensors, actuators)

---

# 🧩 Phase Overview

## Phase 1 – Edge Brain (Local Processing Setup) ✅ START HERE

**Objective:** Build the AI brain first (NO robot required)

### Components (Abstracted for Simulation):

* Compute Environment (your PC / any system capable of running AI models)
* Audio Input Interface
* Audio Output Interface

> Note: Hardware specifics are intentionally abstracted. Focus only on software behavior and interfaces in this phase.

### Software:

* OS: Ubuntu 22.04 LTS (recommended) OR Windows 11 (WSL2 with Ubuntu)
* llama-cpp (TinyLlama / Phi / Mistral small models)

### Execution Environment (Simulation Focus):

* Any system capable of running Python + llama-cpp
* Sufficient RAM for small models (8GB+ recommended)
* Fast storage preferred

### Development Environment:

* Primary Language: Python (Phase 1–3)
* Optional High-Performance Layer: C++ (later phases)
* Python 3.10+
* VS Code
* Git
* WSL2 (if using Windows)
* Docker (optional, recommended for later stability)

### 🧠 Language Strategy (Production-Grade)

* Phase 1–3: Python ✅ (fast development, AI ecosystem)
* Phase 4–6: Python + C++ hybrid (performance-critical parts)
* Phase 7+: Optional Rust/C++ for real-time control

👉 Recommendation:
Start with Python. Optimize later only where needed (do NOT over-engineer early).

### 🐳 Docker Usage Strategy (Important)

* Phase 1 (Now): ❌ NOT required — faster to develop without Docker
* Later Phases: ✅ Use Docker for:

  * Reproducible environment
  * Easy deployment to robot
  * Running services (STT, TTS, AI) as separate containers

👉 Recommendation:
Start WITHOUT Docker. Introduce Docker only after your pipeline is stable.

### What You Should Build Here (Standalone):

* CLI chat with llama-cpp (basic prompt → response)
* Voice input → text (Vosk)
* Text → speech output (Piper)
* Command → Action mapping (VERY IMPORTANT)

  * Example: "Go to dock" → ACTION:DOCK

### Outcome:

* Fully working offline AI assistant
* Can receive commands (text/voice) and respond
* Ready to control robot later

---

### 🔧 Phase 1 – System Simulation Design (VERY IMPORTANT)

Build your AI like a **robot simulator**, not just a chatbot.

### Core Modules to Implement:

1. **Input Listener (Always ON loop)**

   * Continuously listens to microphone
   * Converts audio → text (Vosk)
   * Triggers processing only when input detected

2. **State Manager (Simulated Robot State)**

   * battery_level (0–100)
   * is_charging (true/false)
   * current_location ("room", "dock", etc.)
   * is_idle (true/false)

3. **Decision Engine (llama-cpp)**

   * Input: user command + current state
   * Output: structured response
   * Example:

     * "Battery low" → ACTION:DOCK
     * "Noise detected" → ACTION:INVESTIGATE

4. **Action Executor (Simulation)**

   * Simulates actions instead of real hardware
   * Example:

     * ACTION:DOCK → print("Going to dock...")
     * ACTION:CHARGE → increase battery_level gradually

5. **Background Tasks (Important for future wiring)**

   * Battery drain simulation (every few seconds)
   * Auto-trigger docking when battery < threshold
   * Continuous listening loop

6. **Output System**

   * Text → Speech (Piper)
   * Console logs for debugging

---

### 🧠 Suggested Flow (Architecture)

```
Loop:
  Listen → Convert → Send to AI → Get ACTION → Execute → Update State

Parallel:
  Battery monitor
  Event detection (noise trigger)
```

---

### 🎯 Goal of This Simulation

* Behaves like a real robot WITHOUT hardware
* Fully abstracted from physical components
* Clear separation:

  * AI (decision)
  * State (robot condition)
  * Actions (interfaces)

👉 This design ensures hardware can be plugged in later without changing core logic.

---

## Phase 2 – Basic Mobility (Manual Control)

> Future Note: Hardware integration begins here. All previous logic connects to real-world components.
> **Objective:** Implement physical movement system

### Outcome:

* Robot moves forward/back/turn
* Controlled via external commands

---

## Phase 3 – Vision System

**Objective:** Enable robot to see

### Components:

* USB Camera / Pi Camera
* Optional: Wide-angle lens

### Software:

* OpenCV
* Basic object detection (YOLOv5 nano or similar lightweight model)

### Outcome:

* Live video feed
* Basic object detection (person, obstacles)

---

## Phase 4 – Audio Interface

**Objective:** Listen and speak offline

### Components:

* USB Microphone
* Small Speaker + Amplifier (PAM8403)

### Software:

* Speech-to-text: Vosk (offline)
* Text-to-speech: Piper / Coqui TTS

### Outcome:

* Voice commands
* Robot speaks responses

---

## Phase 5 – Autonomous Navigation (Basic)

**Objective:** Avoid obstacles and move autonomously

### Components:

* Ultrasonic Sensors (HC-SR04) OR
* LiDAR (optional upgrade)
* IMU (MPU6050 optional)

### Software:

* Basic obstacle avoidance logic

### Outcome:

* Moves without hitting objects

---

## Phase 6 – Mapping & Localization

**Objective:** Understand house layout

### Components:

* LiDAR (recommended) OR camera-based SLAM

### Software:

* ROS2
* SLAM Toolbox / RTAB-Map

### Outcome:

* Creates a map of house
* Knows its position

---

## Phase 7 – Docking & Self-Charging

**Objective:** Auto recharge system

### Components:

* Charging dock (metal contacts or wireless pad)
* BMS
* IR beacon / AprilTag / visual marker

### Software:

* Dock detection + path planning

### Outcome:

* Automatically returns to dock when low battery

---

## Phase 8 – Smart Behavior & Monitoring

**Objective:** Intelligent actions

### Features:

* Noise detection → move to source
* Motion detection → record video
* Safe zone detection

### Software:

* Audio event detection
* Vision tracking
* AI decision layer (llama-cpp)

### Outcome:

* Semi-intelligent home assistant robot

---

# 🚀 Final Note (Updated Strategy)

YES — Starting with AI first is the best approach for you.

Build order now:
1 → Brain (software only)
2 → Movement (hardware)
3 → Connect brain ↔ robot
4 → Vision + audio
5 → Autonomy + mapping
6 → Docking
7 → Intelligence

👉 This reduces cost, speeds development, and avoids hardware debugging early.

---

## ✨ Improvements Needed (Actionable)

To make the plan execution-ready, add the following concrete items:

- **Reliability & Fallbacks:** document STT (`Vosk`) and model (`llama-cpp`) failure modes and fallbacks (retries, timeouts, offline confirmation prompts, safe `ACTION:IDLE`).
- **Safety & Motion Constraints:** specify emergency stop, max speed, proximity clamps, watchdog timers, and manual-override behavior before any physical tests.
- **SLAM & Map Format:** pick a SLAM stack (e.g., RTAB-Map or ORB-SLAM2), state the expected map format (occupancy grid / ROS2 map), and define acceptable localization error.
- **Vision Targets:** choose candidate models (YOLOv5-nano, MobileNet-SSD), set target latency and FPS, and list hardware memory/CPU constraints.
- **Testing & Validation:** add unit tests for the Decision Engine (canned state→action cases) and integration scenarios for docking/charging in simulation.
- **Metrics & Logging:** define telemetry (battery, actions, event logs), log retention/rotation, and simple offline dashboards or CSV export for analysis.
- **Reproducibility:** provide `requirements.txt`, an example `Dockerfile` (optional), and platform-specific install/run scripts for Phase‑1.
- **Procurement Checklist (Phase 0):** add a short parts list and minimum specs to avoid procurement delays.

---

## Phase 0 — Parts & Setup Checklist (suggested)

- Compute: Raspberry Pi 4 (4GB) — target platform for Phase‑1 and initial analysis. Use a 64‑bit OS and ARM/NEON runtime builds.
- Model: TinyLlama (quantized GGML/llama.cpp) — baseline on‑device model to fit within Pi 4 (4GB) constraints.
- Microphone: USB mic for Phase‑1 testing
- Speaker: small USB or audio output for TTS testing
- Camera: USB camera (Phase‑3)
- Dock components (Phase‑7): charging contacts + visual marker (AprilTag / IR beacon)
- Optional sensors (Phase‑5): ultrasonic sensors or 2D LiDAR

---

## Phase 1 — Minimal Run Instructions (Phase‑1 PoC)

Add a short runnable example so contributors can get started quickly. Suggested commands to include in a repo `README` or doc:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python examples/phase1_poc/main.py
```

The Phase‑1 PoC should expose a simulated loop: STT stub → Decision Engine (rules + model) → Action Executor (simulated) → state updates + logs.

---

## Notion: Hierarchical TODO (copy into Notion)

Below is a hierarchical checklist formatted for easy copy/paste into Notion. Paste into a Notion page and it will preserve the nested structure.

- [ ] Project: Autonomous 4-Wheeler Robot
  - [ ] Phase 0 — Parts & Setup
    - [ ] Procure compute (Raspberry Pi 4, 4GB)
    - [ ] USB microphone
    - [ ] USB speaker
    - [ ] USB camera
    - [ ] Dock components (contacts / AprilTag)
    - [ ] Optional sensors (ultrasonic / LiDAR)
  - [ ] Phase 1 — Edge Brain (PoC)
    - [ ] Draft Phase‑1 PoC (simulated loop)
    - [ ] Implement STT stub (Vosk integration or mock)
    - [ ] Implement Decision Engine (rules + simple model)
    - [ ] Implement Action Executor (simulation of actions)
    - [ ] Provide Phase‑1 run scripts / README
  - [ ] Reliability & Fallbacks
    - [ ] Document Vosk failure modes and retries
    - [ ] Document llama-cpp timeouts and fallbacks
    - [ ] Add unknown-command confirmation flow
  - [ ] Safety & Motion Constraints
    - [ ] Define emergency stop behavior
    - [ ] Define max speed and proximity clamps
    - [ ] Add watchdog timers and manual override
  - [ ] Navigation / SLAM
    - [ ] Choose SLAM stack (RTAB‑Map / ORB‑SLAM2)
    - [ ] Specify map format (occupancy grid / ROS map)
    - [ ] Define acceptable localization error
  - [ ] Vision
    - [ ] Select lightweight model (YOLOv5‑nano / MobileNet‑SSD)
    - [ ] Define target latency / FPS
    - [ ] Document hardware memory/CPU constraints
  - [ ] Testing & Validation
    - [ ] Unit tests for Decision Engine (canned states → actions)
    - [ ] Integration tests for docking/charging (simulation)
  - [ ] Metrics & Monitoring
    - [ ] Define telemetry fields (battery, actions, events)
    - [ ] Define log retention / rotation policy
  - [ ] Docs & Reproducibility
    - [ ] Add `requirements.txt` and example `Dockerfile`
    - [ ] Add platform-specific install/run scripts

---

If you'd like, I can: create the Phase‑1 scaffold (source files, `requirements.txt`, README, and tests) and update the todo list to track that work.
