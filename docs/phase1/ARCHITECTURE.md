<!-- Moved from docs/ARCHITECTURE.md -->
# Architecture — Phase‑1 (Simulation-first)

High level modules (kept hardware-agnostic):

- Input Listener
  - Responsibility: accept user input (STT or text), normalize commands
  - Phase‑1: console input / STT stub

- State Manager
  - Responsibility: keep internal state (battery_level, is_charging, location, tasks, is_idle)
  - Exposes a thread-safe API for reads/writes

- Decision Engine
  - Responsibility: map input + state -> structured ACTION
  - Phase‑1: deterministic rules + optional small local model

- Action Executor
  - Responsibility: perform or simulate currently supported actions (MOVE, STOP, IDLE, DOCK, ESTOP, RESET_ESTOP, OVERRIDE_ON, OVERRIDE_OFF, MODEL_SUGGESTION)
  - Abstracts hardware interfaces behind commands

- Background Tasks
  - Battery monitor (drain/charge simulation)
  - Event detection stubs (noise/motion)

Design principles
- Keep AI logic separate from hardware adapters
- Keep outputs as structured ACTION tokens
- Build testable decision logic (unit tests with canned states)

## Interface Contracts (Phase-1)

Adapter contracts are intentionally small so production and mock backends remain interchangeable.

- Llama adapter
  - `load_model(model_path: str) -> None`
  - `generate(prompt: str, max_tokens: int = 128, timeout: float | None = None) -> str`

- Audio adapter
  - `record(duration: float) -> bytes`
  - `play(audio_data: bytes) -> None`

- Camera adapter
  - `capture_frame() -> frame`

- Decision output schema
  - `{ "action": str, "params": dict }`
  - Core actions: `STOP`, `DOCK`, `MODEL_SUGGESTION`, `IDLE`

- Executor result schema
  - `{ "status": str, "info": any }`

See `docs/ADAPTERS.md` for full API details.

Target hardware & model (Phase‑1)
- Platform: Raspberry Pi 4 (4GB). The PoC and initial analysis will be performed on a Pi 4 (4GB) to reflect the final deployment environment.
- Model: TinyLlama (quantized for GGML/llama.cpp). Use ARM/NEON builds and aggressive quantization (q4/q8) to fit model memory on 4GB RAM.
- Constraints: expect multi-second to multi‑tens‑of‑seconds latency per response. Use short prompts, caching, and rule-based fallbacks to keep the system responsive.
