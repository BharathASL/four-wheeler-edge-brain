# Autonomous 4-Wheeler Robot (Offline AI)

Project scaffold and Phase‑1 proof-of-concept for an offline, simulation-first autonomous robot brain.

Goals
- Build a local/offline decision engine (Phase‑1)
- Provide a simulated loop that can later be wired to hardware
- Offer clear docs, reproducible setup, and basic tests

Target hardware & model (initial analysis)
- Target platform: Raspberry Pi 4 (4GB) — this is the development and evaluation target for Phase‑1.
- Target model: TinyLlama (quantized GGML/llama.cpp style runtime) for on‑device offline inference.
- Note: expect higher latency and smaller conversational capability compared to 7B+ models; tune prompts and quantization accordingly.

Quick start
1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
```

2. Install minimal deps:

```bash
pip install -r requirements.txt
```

3. Run the Phase‑1 PoC simulation:

```bash
python examples/phase1_poc/main.py
```

Optional: enable text-to-speech output:

```bash
python examples/phase1_poc/main.py --tts
```

Simulation includes a background battery task:

- Battery drains while idle.
- If battery drops to 20% or below, auto-dock is triggered.
- During docking/charging, battery refills in the simulation.

See `docs/` for architecture and roadmap details.

Project task tracking is maintained in `docs/TASK_TRACKER.md`.
