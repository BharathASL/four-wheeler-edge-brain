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
0. On a fresh WSL Ubuntu machine, bootstrap system packages, virtualenv, and Python deps:

```bash
bash scripts/setup_wsl_dev.sh
```

Use `--dry-run` first if you want to inspect the commands before they execute.

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
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
- All runtime defaults live in [`src/config.py`](src/config.py) (`RobotConfig`)

Environment variables (all read once at startup via `RobotConfig.from_env()`):

| Variable | Default | Description |
|---|---|---|
| `MODEL_MODE` | `mock` | `mock` or `real` |
| `MODEL_PATH` | _(empty)_ | Path to `.gguf` model file (required for `real` mode) |
| `LLAMA_LIB_PATH` | _(empty)_ | Optional path to compiled `libllama.so` |
| `MEMORY_DB_PATH` | `data/conversations.sqlite` | SQLite conversation store |
| `MEMORY_RETRIEVAL_MODE` | `fts` | `fts`, `semantic`, or `hybrid` |
| `SEMANTIC_BACKEND` | `auto` | `auto`, `in-memory`, or `faiss` |
| `MODEL_COOLDOWN_SECONDS` | `2.0` | Seconds between model calls |
| `MODEL_TIMEOUT_S` | `5.0` | Model generation timeout (seconds) |
| `TELEMETRY_LOG_DIR` | `data/logs` | Rotating log output directory |
| `TELEMETRY_LOG_MAX_BYTES` | `1048576` | Max log file size before rotation |
| `TELEMETRY_LOG_BACKUP_COUNT` | `3` | Number of backup log files |
| `TELEMETRY_DISABLE_FILE_LOGGING` | `0` | Set to `1`, `true`, or `yes` to disable file logs |
| `HTTP_API_ENABLED` | `0` | Set to `1`, `true`, or `yes` to enable local HTTP API stub |
| `HTTP_API_HOST` | `127.0.0.1` | HTTP API bind host |
| `HTTP_API_PORT` | `8080` | HTTP API bind port |

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

Optional: enable local HTTP API stub (`/health`, `/state`, `/command`):

```bash
python main.py --http-api --http-host 127.0.0.1 --http-port 8080
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

Compare live chat retrieval modes with the same model and memory database:

```bash
python main.py --chat-mode --model-mode real --model-path /absolute/path/to/model.gguf --memory-db-path data/chat_compare.sqlite --retrieval-mode fts --strict-model
python main.py --chat-mode --model-mode real --model-path /absolute/path/to/model.gguf --memory-db-path data/chat_compare.sqlite --retrieval-mode hybrid --semantic-backend in-memory --strict-model
```

Use the same speaker profile and ask the same paraphrased memory questions in both runs to compare grounded recall.

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

WSL-specific setup and audio/camera notes live in `docs/phase1/WSL_AUDIO_CAMERA.md`.

For the concrete pre-hardware validation workflow for the current Blue Yeti microphone, Windows-connected speaker, and Android phone camera path, see `docs/phase1/WSL_DEV_DEVICE_VALIDATION.md`.

Project task tracking is maintained in `docs/TASK_TRACKER.md`.
