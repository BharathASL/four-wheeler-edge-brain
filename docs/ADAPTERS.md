# Adapter API Reference

This document defines the Phase-1 adapter contracts used by the simulation-first architecture.

## Goals

- Keep core logic independent from hardware/runtime details.
- Make unit testing deterministic with mock adapters.
- Keep production adapters swappable by matching the same interface.

## Llama Adapter

Source: src/llama_adapter.py

Class: LlamaAdapter

- __init__(lib_path: Optional[str] = None)
  - Stores optional native library path hint.
- load_model(model_path: str) -> None
  - Attempts lazy runtime init via llama-cpp-python.
  - If runtime is unavailable, keeps adapter in unavailable state.
- generate(prompt: str, max_tokens: int = 128, timeout: Optional[float] = None) -> str
  - Returns model output text.
  - Raises RuntimeError when native runtime is missing.
  - Raises TimeoutError when timeout expires.

Class: MockLlamaAdapter(LlamaAdapter)

- load_model(model_path: str) -> None
- generate(prompt: str, max_tokens: int = 128, timeout: Optional[float] = None) -> str
  - Deterministic response for tests.

## Audio Adapter

Source: src/audio_adapter.py

Class: AudioAdapter

- record(duration: float) -> bytes
  - Contract: return raw audio bytes for duration.
- play(audio_data: bytes) -> None
  - Contract: play bytes to output device.

Class: MockAudioAdapter(AudioAdapter)

- record(duration: float) -> bytes
  - Returns deterministic bytes payload.
- play(audio_data: bytes) -> None
  - No-op in tests.

## Camera Adapter

Source: src/camera_adapter.py

Class: CameraAdapter

- capture_frame() -> Any
  - Contract: return one frame object (usually ndarray in real adapter).

Class: MockCameraAdapter(CameraAdapter)

- capture_frame() -> Tuple[int, int, str]
  - Returns placeholder frame tuple for tests.

## Decision Engine Integration Contract

Source: src/decision_engine.py

DecisionEngine expects a llama-like adapter with:

- generate(prompt, max_tokens=128, timeout=float) -> str

DecisionEngine output schema:

- {"action": str, "params": dict}

Known action values:

- IDLE
- MOVE
- STOP
- DOCK
- ESTOP
- RESET_ESTOP
- OVERRIDE_ON
- OVERRIDE_OFF
- MODEL_SUGGESTION

Known IDLE reasons:

- MODEL_TIMEOUT
- MODEL_UNAVAILABLE

## Input Listener Contract

Source: src/input_listener.py

Class: InputListener

- poll_once() -> Optional[str]

Class: ConsoleInputListener(InputListener)

- poll_once() -> Optional[str]
  - Returns one normalized command.
  - Returns `None` for empty input.
  - Returns `"exit"` on EOF.
- listen_forever(on_command: Callable[[str], None]) -> None
  - Continuously reads commands and forwards to callback.

## Action Executor Contract

Source: src/action_executor.py

Input action schema:

- {"action": str, "params": dict}

Output result schema:

- {"status": str, "info": Any}

Phase-1 supported actions:

- MOVE
- IDLE
- STOP
- ESTOP
- RESET_ESTOP
- DOCK
- OVERRIDE_ON
- OVERRIDE_OFF
- MODEL_SUGGESTION

## State Manager Contract

Source: src/state_manager.py

Class: StateManager

- get(key: str, default: Any = None) -> Any
- set(key: str, value: Any) -> None
- update(**kwargs) -> None
- snapshot() -> Dict[str, Any]

Default state keys:

- battery_level
- is_charging
- location
- tasks
- is_idle

## Telemetry Contract

Source: src/telemetry.py

- init_telemetry(name: str = "four_wheeler", level = logging.INFO, logfile: Optional[str] = None) -> Logger

## Error Handling Rules

- Core loop should treat adapter errors as recoverable whenever possible.
- Runtime-dependent adapters must fail with clear error categories.
- Unit tests should target mock adapters by default.
