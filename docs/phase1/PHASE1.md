<!-- Moved from docs/PHASE1.md -->
# Phase 1 — Edge Brain (TinyLlama on Raspberry Pi 4)

This document describes the Phase‑1 PoC environment, TinyLlama runtime notes, and installation/run steps. Development is carried out on Windows (developer machines) and the production target for Phase‑1 is Raspberry Pi 4 (4GB) running a 64‑bit OS.

## Goals

- Build a hardware‑agnostic PoC that can run on the target Pi with TinyLlama (quantized) and offline audio.
- Provide a reproducible development environment that matches production (same Python environment).
- Validate memory, latency and I/O requirements for the chosen model/runtime.

## Target spec (initial analysis)

- Platform: Raspberry Pi 4 (4GB)
- Model: TinyLlama (quantized GGML style, run via `llama.cpp` / `llama-cpp-python` bindings)

## Environment parity

Because TinyLlama runs as a local runtime (via `llama.cpp`), aim for environment parity while acknowledging native build differences:

- Use the same Python version on dev and Pi (Python 3.10+ recommended).
- Use a virtual environment for both dev and production runs and install from the same `requirements.txt`.
- `llama.cpp` is a native component: compile it for ARM/NEON on the Pi. During Windows development, run with a mocked adapter or use WSL2 for a closer runtime.

Note: native libraries (the `llama.cpp` binary / lib) must be compiled for ARM on the Pi. Keep Python-level code platform-agnostic and provide a mock or adapter so unit tests run on Windows without native binaries.

## Install & setup (recommended)

1. Prepare the Pi with a 64‑bit OS (Ubuntu 22.04 / Raspberry Pi OS 64‑bit) and enable SSH if desired.
2. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install Python requirements (this installs the Python bindings and optional audio packages). For a minimal text-only PoC you may install only `llama-cpp-python` and test-related packages; see `requirements.txt`.

```bash
pip install -r requirements.txt
```

4. Build `llama.cpp` on the Pi (required by `llama-cpp-python`):

- Clone `llama.cpp` and compile with ARM/NEON optimizations. Follow the upstream `llama.cpp` instructions for ARM builds.
- After compiling, ensure the shared library/binary is discoverable by `llama-cpp-python` (it usually locates the library automatically if installed in a standard location).

5. Obtain a quantized TinyLlama GGML model file (q4/q8 recommended for 4GB Pi). Place the model file on the Pi's SSD and note the path. Set `MODEL_PATH` environment variable to the model file location.

## Run the Phase‑1 PoC (text-only / unit test approach)

At this stage we maintain parity between Windows development and the Pi deployment by keeping native calls behind adapters and using tests/mocks on Windows.

- Install dependencies and run unit tests to validate Decision Engine logic (no native `llama.cpp` required for tests).

```bash
pip install -r requirements.txt
pytest -q
```

- When ready to run on the Pi, ensure `llama.cpp` is built and the `MODEL_PATH` environment variable points to the GGML model file, then run the adapter-based script (to be added) which will call `llama-cpp-python`.

## Memory / performance notes

- On a 4GB Pi you must use heavily quantized models (q4/q8 GGML). Even then, model load + inference will be slow; expect seconds to tens of seconds per response.
- Use a fast external SSD (USB3) for model storage and swap to reduce OOM failures.
- Add active cooling to the Pi for sustained inference workloads.

## Production parity checklist

- Use the same `requirements.txt` in dev and production. For Windows-only development without audio or native libs, install selectively or use a virtualenv per workflow.
- Verify `llama.cpp` is compiled on the Pi and works with `llama-cpp-python`.
- Validate one sample inference on the device and measure latency & memory.
- If memory is insufficient, quantify further or reduce context size.

For step-by-step on-device validation, use `docs/phase1/PI_VALIDATION_RUNBOOK.md`.

## Next steps (after Phase‑1 PoC)

- Integrate Vosk (offline STT) into the Input Listener.
- Add a simple TTS (pyttsx3 or Coqui) for audio feedback.
- Add robust fallbacks (model timeouts, retries) and unit tests for the Decision Engine.
