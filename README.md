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
python main.py
```

Model mode selection:

- Default mode is mock (safe for WSL/dev)
- Real llama-cpp mode can be enabled with env vars or CLI flags

Environment-variable example:

```bash
export MODEL_MODE=real
export MODEL_PATH=/absolute/path/to/model.gguf
# optional
export LLAMA_LIB_PATH=/absolute/path/to/libllama.so
python main.py
```

CLI example:

```bash
python main.py --model-mode real --model-path /absolute/path/to/model.gguf
```

Use strict model mode to fail fast instead of falling back to mock:

```bash
python main.py --model-mode real --model-path /absolute/path/to/model.gguf --strict-model
```

Optional: enable text-to-speech output:

```bash
python main.py --tts
```

Test direct chat capabilities (bypasses action mapping and prints model text):

```bash
python main.py --chat-mode --model-mode real --model-path /absolute/path/to/model.gguf --strict-model
```

Chat mode now asks for a speaker name at startup and stores per-speaker conversation history in SQLite.

- If the speaker name is new, a new profile is created.
- If the speaker already exists, previous turns are loaded into the prompt for contextual replies.
- Use `/switch` during chat to change speaker profile.

Tune multi-turn chat memory depth (number of prior user/assistant turns to include):

```bash
python main.py --chat-mode --chat-history-turns 6 --model-mode real --model-path /absolute/path/to/model.gguf --strict-model
```

Enable long-history retrieval from older conversations (SQLite FTS):

```bash
python main.py --chat-mode --chat-history-turns 6 --retrieval-turns 4 --strict-model
```

Enable retrieval benchmark hooks (prints latency/hit metrics on exit):

```bash
python main.py --chat-mode --benchmark-memory-retrieval --strict-model
```

Run migration-gate evaluator (recall@k + latency percentiles over fixed query set):

```bash
python scripts/evaluate_migration_gate.py --output-json data/migration_gate_report.json
```

The evaluator exits with code 0 when thresholds pass and 2 when thresholds fail.

Run AI action evaluation harness (prompt set + expected action classes):

```bash
python scripts/evaluate_ai_harness.py --output-json data/ai_eval_report.json
```

The harness exits with code 0 when accuracy threshold passes and 2 when it fails.

Optional: override memory database location:

```bash
python main.py --chat-mode --memory-db-path data/conversations.sqlite
```

Simulation includes a background battery task:

- Battery drains while idle.
- If battery drops to 20% or below, auto-dock is triggered.
- During docking/charging, battery refills in the simulation.

See `docs/` for architecture and roadmap details.

Project task tracking is maintained in `docs/TASK_TRACKER.md`.
