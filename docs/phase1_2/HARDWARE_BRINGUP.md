# Phase 1.2 - Hardware Bring-Up

This document is the practical bring-up guide for moving from the current simulation-first Phase 1 runtime to Raspberry Pi-hosted hardware validation for Phase 1.2.

The goal is to prepare everything that can be prepared before hardware arrives, then provide a controlled sequence for first power-on, software validation, and initial motor-interface testing once the Raspberry Pi and motor components are available.

## Objectives And Scope

Phase 1.2 bring-up is intentionally narrow.

Objectives:
- Prepare a Raspberry Pi environment that can run the existing Phase 1 runtime and tests.
- Validate that the repo installs cleanly in a project virtualenv using the shared `requirements.txt` workflow.
- Confirm that the current software stack still behaves correctly on Pi before any real motor wiring is introduced.
- Move from pure simulation to hardware-adjacent validation in small, reversible steps.
- Define the checkpoints required before physical motor movement is allowed.

In scope for this phase:
- Pi OS provisioning and base package preparation.
- Repository checkout, virtualenv setup, and Python dependency installation.
- Model/runtime preparation for local inference where supported by the available hardware.
- Validation of the existing simulation, safety, and adapter paths on the Pi.
- Documentation of the motor backend placeholder and the remaining hardware decisions.

Out of scope for this phase:
- Claiming production-ready GPIO/PWM motor control.
- Claiming real sensor integration.
- Claiming hardware ESTOP wiring or a deadman circuit.
- Full physical mobility testing before a motor driver board, wiring plan, and backend implementation exist.

## Current Software Status

The current repository already contains the software pieces needed to prepare for hardware bring-up, but not the final hardware control path.

Available now:
- `main.py` runs the simulation-first Phase 1 runtime.
- `src/action_executor.py` executes `MOVE`, `STOP`, `IDLE`, `DOCK`, `ESTOP`, `RESET_ESTOP`, `OVERRIDE_ON`, `OVERRIDE_OFF`, and `MODEL_SUGGESTION` actions.
- `src/safety_controller.py` applies movement clamps before execution.
- `src/motor_adapter.py` defines the motor adapter contract plus a backend-facing PWM stub and a deterministic mock adapter.
- `src/background_tasks.py` includes a command watchdog path that can request a safe stop on stale command state.
- `tests/test_motor_adapter.py` and `tests/test_phase1_1_safety.py` already validate key motor-adapter, ESTOP, and safety behavior.

Important limitation:
- The real motor hardware path does not exist yet. `PWMMotorAdapter` only delegates to an injected backend object. It does not implement Raspberry Pi GPIO access, PWM generation, pin mapping, or motor-driver-specific logic.

## Prerequisites For Raspberry Pi Bring-Up

Expected target environment:
- Raspberry Pi 4 (4 GB) for the initial target.
- Ubuntu Server 24.04 64-bit.
- Python 3.10+.
- SSH access enabled.
- Network connectivity for package installation and repository checkout.

Recommended hardware to have available before physical bring-up:
- Raspberry Pi, power supply, SD card or SSD boot media.
- Cooling appropriate for sustained local inference.
- Keyboard/monitor or headless SSH workflow.
- Motor driver board or HAT once selected.
- Safe motor power source separate from Pi logic power.
- Accessible emergency stop procedure before any wheel actuation test.

If the Pi has not arrived yet, this guide is still useful for preparing:
- The exact repository setup steps.
- The validation sequence to run on first boot.
- The decisions that must be made before any real motor test.

## Repo And Environment Setup

Use the same project pattern already documented for development: a Python virtualenv plus `requirements.txt`.

1. Provision Ubuntu Server 24.04 on the Pi.
   - Flash Ubuntu Server 24.04 64-bit.
   - Configure hostname, user, SSH, and network during imaging or on first boot.
   - Apply system updates before installing project dependencies.

2. Install base packages.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip build-essential
```

3. Clone the repository.

```bash
git clone <repo-url> four-wheeler-robot
cd four-wheeler-robot
```

4. Create and activate the project virtualenv.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

5. Install Python dependencies.

```bash
pip install -r requirements.txt
```

6. Optional model runtime environment.
   - Set `MODEL_PATH` to a local GGUF file if testing real inference.
   - Set `LLAMA_LIB_PATH` only if a compiled shared library must be pointed to explicitly.
   - Keep mock mode as the default fallback when the native runtime is not available.

7. Run the simulation entrypoint before attempting any hardware-specific work.

```bash
python main.py
```

## Expected Components Already Available In Repo

The following software capabilities should already work before hardware-specific decisions are made:

- Simulation-first control loop and command processing.
- Rule-first action mapping with safe fallbacks.
- Action execution with stop, ESTOP, override, and simulated move paths.
- Max speed and proximity clamping in `src/safety_controller.py`.
- Mock motor adapter support for deterministic testing.
- Watchdog-triggered stop requests on stale control state.
- Telemetry/logging support.

This means the first Pi validation target is not real movement. The first target is reproducing the existing simulation and safety behavior on Pi hardware.

## Motor Adapter Status And Current Limitations

Current status:
- `MotorAdapter` defines the basic contract: `set_motion(linear_mps, angular_dps)` and `stop()`.
- `PWMMotorAdapter` is a backend-facing stub.
- `MockMotorAdapter` is the current deterministic implementation used for tests.

What is implemented today:
- `ActionExecutor` uses `clamp_movement_action(...)` before issuing motion.
- If a motor adapter is present, `ActionExecutor` calls `set_motion(...)` on the adapter.
- If no motor adapter is configured, movement remains simulated.
- If a motor adapter raises an error during movement, `ActionExecutor` attempts `stop()` and latches ESTOP.

What is not implemented today:
- Raspberry Pi GPIO pin control.
- PWM duty-cycle generation.
- Direction pin logic.
- Motor-driver-specific backend code.
- Wheel calibration, ramping, or encoder feedback.
- Hardware ESTOP input wiring.

Practical implication:
- The repo is ready for backend integration and safe validation steps.
- The repo is not ready to drive motors directly without an additional backend implementation tied to the selected motor hardware.

## Safe Bring-Up Sequence

Use this sequence exactly to avoid mixing multiple unknowns at once.

### Stage 0 - Pre-Hardware Preparation

Complete these items before the Pi or motor hardware arrives:
- Read this guide, `README.md`, and `docs/phase1/DEPLOYMENT.md`.
- Decide where the Pi will store the repository, virtualenv, logs, and model files.
- Decide whether Phase 1.2 will use mock model mode first or real model mode.
- Review `src/motor_adapter.py`, `src/action_executor.py`, and `src/safety_controller.py` so backend integration constraints are clear.

### Stage 1 - Pi Software Bring-Up

On first Pi boot:
- Complete OS updates.
- Clone the repository.
- Create the project virtualenv.
- Install `requirements.txt`.
- Run targeted tests first.
- Run `python main.py` in mock/default mode.

Success criteria for Stage 1:
- Virtualenv activation works.
- Dependencies install successfully.
- Unit tests covering motor/safety behavior pass.
- The runtime starts on Pi without requiring hardware adapters.

### Stage 2 - Pi Runtime Validation Without Motor Hardware

Validate that the software behaves the same on Pi as it does in development:
- Confirm `MOVE` actions remain simulated when no motor adapter is configured.
- Confirm `STOP` and `ESTOP` paths return safe responses.
- Confirm override and watchdog behavior still work.
- If testing real inference, verify the configured local model loads without destabilizing the rest of the runtime.

Do not connect motors yet.

### Stage 3 - Backend Interface Validation Before Wiring Motors

Only start this stage after a motor driver board or HAT is selected.

Required decisions before proceeding:
- Which motor driver board or HAT will be used.
- Which GPIO library or backend will generate PWM and direction signals.
- How Pi logic power and motor power will be isolated.
- How an operator will trigger an immediate safe stop during testing.

Recommended first backend milestone:
- Implement a backend object that satisfies the existing `PWMMotorAdapter` expectation by exposing `set_motion(...)` and `stop()`.
- Validate that backend calls can be made without motors connected, ideally by observing logs, debug output, or non-loaded signal outputs.

### Stage 4 - Low-Risk Hardware-Adjacent Tests

After a backend exists and wiring is reviewed:
- Power the Pi separately from the motor power path if the design requires it.
- Keep wheels lifted or mechanically unloaded for the first signal tests.
- Start with explicit `STOP` validation.
- Test minimal forward and turn commands at the lowest reasonable duty cycle.
- Confirm `ESTOP` and manual reset work before any longer-duration command is attempted.

Abort immediately if:
- The Pi browns out or reboots.
- A stop command does not stop motion promptly.
- Motor direction is inverted unexpectedly.
- The backend behaves differently from the expected adapter contract.

## GPIO, PWM, And Backend Placeholders

These design points remain intentionally undecided in the current codebase:

- Motor driver board / HAT selection.
- GPIO library choice.
- PWM frequency and duty-cycle mapping.
- Direction pin layout.
- Linear/angular velocity to left/right wheel conversion.
- Ramp limits or acceleration smoothing.
- Encoder and odometry integration.
- Hardware ESTOP input method.

Until those decisions are made, use the following rule:
- Treat `PWMMotorAdapter` as an integration seam, not as a completed hardware driver.

## Validation Checklist

Use this checklist during bring-up.

Before Pi arrival:
- Phase 1 runtime behavior reviewed.
- Safety and ESTOP expectations reviewed.
- Motor backend contract reviewed.
- Bring-up sequence agreed.

After Pi setup:
- Ubuntu Server 24.04 64-bit installed.
- SSH access confirmed.
- System packages updated.
- Repository cloned successfully.
- `.venv` created and activated.
- `pip install -r requirements.txt` completed.

Software validation on Pi:
- `python main.py` starts in safe default mode.
- Targeted motor/safety tests pass.
- Simulation path works without a motor adapter.
- ESTOP latch/reset behavior is verified.
- Watchdog stop behavior is verified if exercised locally.

Before live motor actuation:
- Motor board selected and documented.
- Backend implementation exists for `PWMMotorAdapter`.
- Wiring reviewed.
- Safe stop procedure defined.
- Wheels unloaded or robot physically restrained for initial tests.

## Phase 1.2 Exit Criteria (Objective Gate)

Phase 1.2 should only be marked complete when all required gates below pass and
the evidence artifacts are captured.

### Gate A - Environment And Install

Pass when all are true:
- Pi provisioning is complete (OS, hostname/user/SSH/network).
- Repository is cloned on Pi.
- Virtualenv activation succeeds.
- `pip install -r requirements.txt` succeeds.

Evidence:
- Setup command transcript and final successful command outputs.

### Gate B - Software Baseline

Pass when all are true:
- `pytest -q` runs on Pi and exits with code 0.

Evidence:
- Pytest summary output stored in run log.

### Gate C - Inference Runtime

Pass when all are true:
- Runtime/model load path succeeds using the runbook inference check.
- At least one real inference completes with non-empty output.
- Latency for that run is recorded.

Evidence:
- Inference script output including `OUTPUT:` and `LATENCY_SEC:`.

### Gate D - Decision Path Integration

Pass when all are true:
- DecisionEngine integration check returns a dict.
- Result contains both `action` and `params` keys.
- No native runtime crash occurs in this path.

Evidence:
- Decision integration command output and returned dict payload.

### Gate E - Safety Path (Software)

Pass when all are true:
- STOP/ESTOP software behavior is validated in simulation-safe path.
- ESTOP reset behavior is confirmed (`RESET_ESTOP` required before movement).

Evidence:
- Command transcript showing expected ESTOP latch and reset semantics.

### Gate F - Resource Snapshot

Pass when all are true:
- Memory snapshot captured (`free -h`).
- CPU/temperature snapshot captured (`vcgencmd measure_temp` when available).
- Basic process snapshot captured (`top -b -n1 | head -n 20`).

Evidence:
- Snapshot outputs archived with timestamp.

### Conditional Motor Gate (When Hardware Is Available)

This gate is required to close full hardware bring-up once motor hardware exists,
but it is not applicable while motor tasks remain hardware-blocked.

Pass when all are true:
- Motor board/HAT is selected and documented.
- Backend implementation is present for `PWMMotorAdapter`.
- Basic unloaded spin/stop tests are successful with safe stop procedure in place.

Evidence:
- Backend test logs, wiring notes, and unloaded spin validation record.

### Phase-Close Rule

Mark `Phase 1.2` as complete only when:
- Gates A through F are PASS, and
- Conditional Motor Gate is PASS when hardware is available, and
- Evidence artifacts are recorded in the runbook result log.

## Failure, Rollback, And Safety Notes

Safety expectations for Phase 1.2:
- `ESTOP` is a software latch in the current implementation.
- `RESET_ESTOP` is required before movement resumes after an ESTOP latch.
- Movement requests are clamped to the configured max linear and angular limits.
- Forward movement is blocked when the current proximity thresholds are violated.
- Backend errors during movement should trigger a stop attempt and latch ESTOP.

Current clamp values:
- `MAX_LINEAR_SPEED_MPS = 0.35`
- `MAX_ANGULAR_SPEED_DPS = 45.0`
- `MIN_FRONT_PROXIMITY_M = 0.35`
- `MIN_SIDE_PROXIMITY_M = 0.20`

Failure handling guidance:
- If Pi setup fails, revert to the last known-good virtualenv and rerun in mock mode.
- If the model runtime fails to load, continue in mock mode rather than blocking all bring-up work.
- If backend integration fails, disconnect or disable the backend and return to simulation-only validation.
- If a physical test behaves unexpectedly, stop immediately and return to unloaded validation.

Important safety note:
- The current repository does not implement a hardware ESTOP circuit, relay cutoff, or physical deadman path. Software ESTOP is necessary but not sufficient for unattended real-world motion.

## Deferred Until Hardware Is Selected Or Available

The following work is explicitly deferred:
- Final motor driver board selection.
- Concrete GPIO/PWM backend implementation.
- Signal mapping from velocity commands to wheel outputs.
- Physical wiring verification and spin tests.
- Real sensor drivers feeding live proximity values.
- Hardware ESTOP button or cutoff circuit.
- Movement calibration and any closed-loop motor control.
- Phase 1.2 exit validation that requires the Pi and motors responding together.

## Document Maintenance Criteria

This document itself is considered up-to-date when:
- The repository setup path is clear for a new Pi.
- The current implementation boundaries are explicit.
- The transition path from simulation to hardware is staged and reversible.
- The remaining undecided hardware items are listed clearly.
- No section implies hardware support that the repo does not yet implement.

Last updated: 2026-03-27