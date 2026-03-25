<!-- Moved from docs/ARCHITECTURE_TASKS.md -->
# Architecture & Implementation Tasks

This file lists the architecture overview and a task checklist for Phase‑1 and early work. We'll update this file and mark items completed as we finish them.

## Architecture Summary

- Core logic: decision engine, state manager, rules (portable across platforms)
- Model adapter: TinyLlama via `llama-cpp-python` (`llama.cpp` native lib on Pi)
- Audio adapter: capture/playback (sounddevice/PortAudio) with mock backend for tests
- Camera adapter: OpenCV backend with mock for dev
- Action executor: hardware drivers + simulation stubs
- Background services: battery monitor, event detector, telemetry
- Interface: CLI / HTTP API for production; optional GUI for dev only

## Task Checklist (mark items as completed when done)

- [x] Draft Phase‑1 PoC scaffold (examples, README)
- [x] Create `src/llama_adapter.py` (real + mock adapter) — completed 2026-03-25
- [x] Create `src/audio_adapter.py` (sounddevice + mock) — completed 2026-03-25
- [x] Create `src/camera_adapter.py` (OpenCV + mock) — completed 2026-03-25
- [x] Create `src/decision_engine.py` and `src/state_manager.py` — completed 2026-03-25
- [x] Create `src/action_executor.py` and hardware adapter stubs — completed 2026-03-25
- [x] Add unit tests for Decision Engine (mock adapters) — completed 2026-03-26 (added tests + conftest to ensure imports)
- [x] Add timeout and runtime error handling for model calls (`LlamaAdapter`, `DecisionEngine`) — completed 2026-03-26
- [x] Add telemetry & logging module (`src/telemetry.py`) — completed 2026-03-25
- [x] Add runtime entrypoint for Phase‑1 PoC (`main.py`) — completed 2026-03-26
- [x] Add deployment docs and systemd unit example (`docs/phase1/DEPLOYMENT.md`, `docs/phase1/robot.service`) — completed 2026-03-26
- [x] Create portable audio+camera template (WSLg + Pi) — completed 2026-03-26 (`docs/phase1/PORTABLE_AUDIO_CAMERA_TEMPLATE.md`)
- [x] Design and document robot software architecture (adapters + interfaces) — completed 2026-03-26 (`docs/phase1/ARCHITECTURE.md`, `docs/ADAPTERS.md`)
- [x] CI: Windows job (unit tests with mocks); optional ARM job for smoke tests — completed 2026-03-26
- [x] Documentation: adapter API reference (`docs/ADAPTERS.md`) — completed 2026-03-26

## How we'll use this file

- I will update the checkboxes as I implement each item. To mark an item completed, I'll change `[ ]` to `[x]` and add a short note with timestamp.
- If you prefer, I can also keep the `manage_todo_list` in sync with this file.

---

Last updated: 2026-03-26
