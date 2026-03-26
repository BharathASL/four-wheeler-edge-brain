# Phase-1 Raspberry Pi Validation Runbook

This runbook validates the hardware-dependent parts that cannot be fully verified in Windows/WSL CI.

## Scope

- Build and load `llama.cpp` runtime on Raspberry Pi.
- Validate one real TinyLlama inference from Python.
- Verify latency and memory characteristics.
- Smoke-check camera and audio device availability.

## Preconditions

- Raspberry Pi 4 (4GB), 64-bit OS.
- Repository checked out on Pi.
- Quantized TinyLlama model file present (recommended q4/q8).
- Model stored on SSD when possible.

## Environment Setup

```bash
cd /path/to/four-wheeler-robot
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If `llama.cpp` is not built yet, follow `docs/phase1/TINYLLAMA_SETUP.md` first.

Set required environment variables:

```bash
export MODEL_PATH=/absolute/path/to/tinyllama-q4.bin
# Optional, if library auto-discovery fails
export LLAMA_LIB_PATH=/absolute/path/to/libllama.so
export ROBOT_ENV=prod
```

One-command helper (recommended):

```bash
chmod +x scripts/phase1_validate_pi.sh
./scripts/phase1_validate_pi.sh
```

## Test 1: Unit Test Baseline on Pi

Goal: Confirm Python environment is healthy on device.

```bash
pytest -q
```

Pass criteria:

- Test suite exits with code 0.

## Test 2: Runtime Load + Single Inference

Goal: Verify native runtime works on Pi and model can produce output.

```bash
python - <<'PY'
import os
import time
from src.llama_adapter import LlamaAdapter

model_path = os.environ.get("MODEL_PATH")
if not model_path:
    raise SystemExit("MODEL_PATH is required")

adapter = LlamaAdapter(lib_path=os.environ.get("LLAMA_LIB_PATH"))
adapter.load_model(model_path)

prompt = "Return one short action token for: battery low go charge"
t0 = time.perf_counter()
out = adapter.generate(prompt, max_tokens=24, timeout=30)
elapsed = time.perf_counter() - t0

print("OUTPUT:", out.strip())
print("LATENCY_SEC:", round(elapsed, 3))
PY
```

Pass criteria:

- No `RuntimeError` from missing runtime.
- No timeout for this short prompt under normal load.
- Non-empty output string.

## Test 3: Decision Engine Integration

Goal: Validate app-level path using real model adapter.

```bash
python - <<'PY'
import os
from src.llama_adapter import LlamaAdapter
from src.decision_engine import DecisionEngine

adapter = LlamaAdapter(lib_path=os.environ.get("LLAMA_LIB_PATH"))
adapter.load_model(os.environ["MODEL_PATH"])
engine = DecisionEngine(llama_adapter=adapter, model_timeout=30.0)

state = {"battery_level": 18, "is_charging": False, "is_idle": True}
result = engine.decide("what should I do now", state)
print(result)
PY
```

Pass criteria:

- Returns a dict with keys `action` and `params`.
- No crash due to native runtime issues.

## Test 4: Memory and Thermals Spot Check

Goal: Capture basic operational envelope.

Run during Test 2/3 in another shell:

```bash
free -h
vcgencmd measure_temp || true
top -b -n1 | head -n 20
```

Record:

- Peak memory usage estimate.
- CPU temperature.
- Whether throttling or OOM symptoms occurred.

## Test 5: Camera and Audio Device Presence (Optional for Phase-1)

Goal: Verify OS-level device visibility for future real I/O integration.

```bash
ls /dev/video* || true
arecord -l || true
aplay -l || true
```

Pass criteria:

- Expected devices are listed when hardware is connected.

## Result Log Template

Fill this table after each run:

| Date | Pi Model | Model Quant | Prompt Tokens | Latency (s) | Peak Mem | Temp | Result |
|---|---|---|---:|---:|---|---|---|
| YYYY-MM-DD | Pi 4 4GB | q4 | 24 |  |  |  | PASS/FAIL |

## Troubleshooting

- Runtime unavailable:
  - Confirm `llama.cpp` build exists and `LLAMA_LIB_PATH` points to `libllama.so`.
- Timeout in inference:
  - Reduce prompt/context, lower `max_tokens`, use more aggressive quantization.
- OOM or heavy swapping:
  - Move model to SSD, reduce context/tokens, verify swap configuration.
- Thermal throttling:
  - Improve cooling and rerun with reduced load.

## Exit Criteria for Phase-1 Hardware Validation

- Unit tests pass on Pi.
- At least one successful real inference with recorded latency.
- DecisionEngine integration run completes without runtime error.
- Basic memory/thermal observations are captured.
