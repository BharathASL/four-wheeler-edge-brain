---
name: Copilot Workspace Instructions
description: Repository-wide instructions for Copilot behavior and project constraints.
---

# Project: Autonomous 4‑Wheeler Robot — Workspace Instructions

Purpose
- Describe the project's development vs production environment and give clear instructions so contributors and tooling (Copilot/agents) can work consistently.

Environments
- Development: WSL2 + WSLg using Ubuntu 24.04. Use a Python virtual environment and the repository `requirements.txt` for all Python dependencies.
- Production targets:
    - Phase 1: Raspberry Pi 4 (4GB) on Ubuntu Server 24.04.
    - Later phases: Raspberry Pi 5 (8GB recommended), while keeping portability across supported Pi models.
- Code must support both development and production environments at all times.

Principles
- Environment parity: keep `requirements.txt` identical for dev and prod where possible. Native components (compiled libraries) will differ and must be built on the target platform.
- Platform detection: code must detect runtime platform and load platform-specific adapters or compiled libraries safely.
- Fail safe: when a native runtime or model cannot be loaded (e.g., missing ARM lib in WSL or on an unprepared Pi), fall back to a mock or a lightweight stub.

Files to consult
- Project README: [README.md](../README.md)
 - Phase 1: [docs/phase1/PHASE1.md](../docs/phase1/PHASE1.md)
 - Phase 1 setup: [docs/phase1/TINYLLAMA_SETUP.md](../docs/phase1/TINYLLAMA_SETUP.md)
- Architecture notes: [docs/phase1/ARCHITECTURE.md](../docs/phase1/ARCHITECTURE.md)
- Roadmap: [docs/ROADMAP.md](../docs/ROADMAP.md)
- Python deps: [requirements.txt](../requirements.txt)

Quick rules for contributors
1. Use the same Python version locally and on the Pi (3.10+ recommended).
2. Always install dependencies from `requirements.txt` in a virtualenv.
3. Do not commit built binaries for `llama.cpp` or similar native libs — build them on the Pi or in CI for ARM.
4. Add code that checks for platform before importing or calling native libraries.

Platform detection (recommended snippet)

```python
import platform
IS_PI = platform.machine().startswith('arm') or 'raspberry' in platform.uname().node.lower()
IS_WSL = 'microsoft' in platform.uname().release.lower() or 'wsl' in platform.uname().release.lower()

if IS_PI:
    # import or load ARM/NEON-compiled library
    pass
elif IS_WSL:
    # import WSL-friendly stub or Linux dev binary
    pass
```

Native libraries & model runtime
- `llama.cpp` (GGML) must be compiled for ARM on the Pi. The Python package `llama-cpp-python` expects a compiled library or will use a system-installed shared library.
- Build `llama.cpp` on the Pi (or cross-compile in CI) and document the build steps in `docs/phase1/TINYLLAMA_SETUP.md` (TODO).
- Model files (GGML .bin) should be stored on external SSD (recommended) and not checked in to the repo. Use `MODEL_PATH` environment variable to point to the model file.

Environment variables (suggested)
- `MODEL_PATH` — filesystem path to the TinyLlama GGML file on device.
- `LLAMA_LIB_PATH` — optional path to compiled `llama.cpp` shared library.
- `ROBOT_ENV` — `dev` or `prod` (useful for tests and CI)

Development on WSL2 / WSLg (Ubuntu 24.04)
- Create virtualenv and install `requirements.txt`.
- Mock or skip ARM-only native calls; provide a `mocks/` adapter for local testing.
- Keep development inside the Ubuntu 24.04 WSL environment; do not rely on native Windows Python support.

Production on Raspberry Pi 5
- Use Ubuntu Server 24.04 64‑bit.
- Create a venv and install Python deps.
- Build `llama.cpp` on the Pi with ARM/NEON optimizations; ensure the compiled lib is present for `llama-cpp-python`.

Testing & CI
- Keep unit tests independent of native binaries by mocking the model runtime.
- CI should run Python unit tests on Ubuntu 24.04 and, if possible, include a separate job that builds `llama.cpp` for ARM and runs basic smoke tests via QEMU or an ARM runner.

Developer UX
- If code detects that the native runtime is missing, provide a clear message with suggested commands (how to build on Pi or complete the WSL setup). Do not crash silently.

Conventions for changes
- If adding native dependencies, update `docs/phase1/TINYLLAMA_SETUP.md` and add clear build steps for the Pi.
- If changing `requirements.txt`, ensure the package is available on both platforms or document platform-specific install steps.
- Treat `docs/TASK_TRACKER.md` as the planning source of truth.
- If scope, plan, phase, priority, or task status changes, update `docs/TASK_TRACKER.md` in the same change.

Contact / maintainer note
- Add maintainers in the repo `README.md` with contact details and recommended Pi hardware and model information.

---

If you want, I can also add `docs/phase1/TINYLLAMA_SETUP.md` with concrete `llama.cpp` build commands for Raspberry Pi 5 and an example `MODEL_PATH` loader. Reply with "Add build doc" to proceed.
