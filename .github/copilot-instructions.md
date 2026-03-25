---
title: Copilot / Workspace Instructions
--

# Project: Autonomous 4‑Wheeler Robot — Workspace Instructions

Purpose
- Describe the project's development vs production environment and give clear instructions so contributors and tooling (Copilot/agents) can work consistently.

Environments
- Development: Windows (primary development environment). Use a Python virtual environment and the repository `requirements.txt` for all Python dependencies.
- Production target: Raspberry Pi 5 (recommend 8GB). Code must support both environments at all times.

Principles
- Environment parity: keep `requirements.txt` identical for dev and prod where possible. Native components (compiled libraries) will differ and must be built on the target platform.
- Platform detection: code must detect runtime platform and load platform-specific adapters or compiled libraries safely.
- Fail safe: when a native runtime or model cannot be loaded (e.g., missing ARM lib on Windows), fall back to a mock or a lightweight stub.

Files to consult
- Project README: [README.md](README.md)
 - Phase 1: [docs/phase1/PHASE1.md](docs/phase1/PHASE1.md)
 - Phase 1 setup: [docs/phase1/TINYLLAMA_SETUP.md](docs/phase1/TINYLLAMA_SETUP.md)
- Architecture notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- Python deps: [requirements.txt](requirements.txt)

Quick rules for contributors
1. Use the same Python version locally and on the Pi (3.10+ recommended).
2. Always install dependencies from `requirements.txt` in a virtualenv.
3. Do not commit built binaries for `llama.cpp` or similar native libs — build them on the Pi or in CI for ARM.
4. Add code that checks for platform before importing or calling native libraries.

Platform detection (recommended snippet)

```python
import platform
IS_PI = platform.machine().startswith('arm') or 'raspberry' in platform.uname().node.lower()
IS_WINDOWS = platform.system() == 'Windows'

if IS_PI:
    # import or load ARM/NEON-compiled library
    pass
elif IS_WINDOWS:
    # import Windows-friendly stub or local dev binary
    pass
```

Native libraries & model runtime
- `llama.cpp` (GGML) must be compiled for ARM on the Pi. The Python package `llama-cpp-python` expects a compiled library or will use a system-installed shared library.
- Build `llama.cpp` on the Pi (or cross-compile in CI) and document the build steps in `docs/TINYLLAMA_SETUP.md` (TODO).
- Model files (GGML .bin) should be stored on external SSD (recommended) and not checked in to the repo. Use `MODEL_PATH` environment variable to point to the model file.

Environment variables (suggested)
- `MODEL_PATH` — filesystem path to the TinyLlama GGML file on device.
- `LLAMA_LIB_PATH` — optional path to compiled `llama.cpp` shared library.
- `ROBOT_ENV` — `dev` or `prod` (useful for tests and CI)

Development on Windows
- Create virtualenv and install `requirements.txt`.
- Mock or skip ARM-only native calls; provide a `mocks/` adapter for local testing.
- Optionally use WSL2 with Ubuntu to build cross-platform native binaries.

Production on Raspberry Pi 5
- Use a 64‑bit OS (Ubuntu 22.04 or Raspberry Pi OS 64‑bit).
- Create a venv and install Python deps.
- Build `llama.cpp` on the Pi with ARM/NEON optimizations; ensure the compiled lib is present for `llama-cpp-python`.

Testing & CI
- Keep unit tests independent of native binaries by mocking the model runtime.
- CI should run Python unit tests on Windows (dev) and, if possible, include a separate job that builds `llama.cpp` for ARM and runs basic smoke tests via QEMU or an ARM runner.

Developer UX
- If code detects that the native runtime is missing, provide a clear message with suggested commands (how to build on Pi or enable WSL build). Do not crash silently.

Conventions for changes
- If adding native dependencies, update `docs/TINYLLAMA_SETUP.md` and add clear build steps for the Pi.
- If changing `requirements.txt`, ensure the package is available on both platforms or document platform-specific install steps.

Contact / maintainer note
- Add maintainers in the repo `README.md` with contact details and recommended Pi hardware and model information.

---

If you want, I can also add `docs/TINYLLAMA_SETUP.md` with concrete `llama.cpp` build commands for Raspberry Pi 5 and an example `MODEL_PATH` loader. Reply with "Add build doc" to proceed.
