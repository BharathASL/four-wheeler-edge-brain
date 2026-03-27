#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

print_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

print_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

print_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

run_step() {
  local title="$1"
  shift
  echo
  echo "== $title =="
  if "$@"; then
    print_pass "$title"
  else
    print_fail "$title"
  fi
}

check_env() {
  if [[ -z "${MODEL_PATH:-}" ]]; then
    echo "MODEL_PATH is not set"
    return 1
  fi
  if [[ ! -f "$MODEL_PATH" ]]; then
    echo "MODEL_PATH does not point to a file: $MODEL_PATH"
    return 1
  fi
  return 0
}

run_pytest() {
  cd "$ROOT_DIR" || return 1
  pytest -q
}

run_runtime_inference() {
  cd "$ROOT_DIR" || return 1
  python - <<'PY'
import os
import time
from src.llama_adapter import LlamaAdapter

model_path = os.environ["MODEL_PATH"]
adapter = LlamaAdapter(lib_path=os.environ.get("LLAMA_LIB_PATH"))
adapter.load_model(model_path)

prompt = "Return one short action token for: battery low go charge"
t0 = time.perf_counter()
out = adapter.generate(prompt, max_tokens=24, timeout=30)
elapsed = time.perf_counter() - t0

print("OUTPUT:", out.strip())
print("LATENCY_SEC:", round(elapsed, 3))
PY
}

run_decision_engine_check() {
  cd "$ROOT_DIR" || return 1
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

if not isinstance(result, dict):
    raise SystemExit("result is not dict")
if "action" not in result or "params" not in result:
    raise SystemExit("result missing action/params")
PY
}

collect_system_snapshot() {
  echo
  echo "== System Snapshot =="
  free -h || true
  vcgencmd measure_temp || true
  top -b -n1 | head -n 20 || true

  echo
  echo "== Device Presence =="
  ls /dev/video* 2>/dev/null || print_warn "No video devices detected"
  arecord -l || print_warn "No capture devices detected or arecord unavailable"
  aplay -l || print_warn "No playback devices detected or aplay unavailable"
  return 0
}

main() {
  echo "Phase-1 Pi validation helper"
  echo "Repository: $ROOT_DIR"

  run_step "Check required environment" check_env

  if [[ $FAIL_COUNT -eq 0 ]]; then
    run_step "Run unit tests (pytest)" run_pytest
    run_step "Runtime load + single inference" run_runtime_inference
    run_step "DecisionEngine integration" run_decision_engine_check
    run_step "Collect system and device snapshot" collect_system_snapshot
  else
    print_warn "Skipping runtime checks due to earlier failure"
  fi

  echo
  echo "Summary: PASS=$PASS_COUNT FAIL=$FAIL_COUNT"

  # Gate summary — maps to Phase 1.2 objective exit criteria in HARDWARE_BRINGUP.md
  echo
  echo "== Phase 1.2 Gate Summary =="
  echo "PHASE1_2_GATE_A_ENV=$(      [[ $FAIL_COUNT -eq 0 ]] && echo PASS || echo FAIL )"
  echo "PHASE1_2_GATE_B_TESTS=$(    [[ $FAIL_COUNT -eq 0 ]] && echo PASS || echo FAIL )"
  echo "PHASE1_2_GATE_C_INFERENCE=$(python -c 'import os; p=os.environ.get("MODEL_PATH",""); print("PASS" if p and __import__("os").path.isfile(p) else "SKIP")' 2>/dev/null || echo SKIP)"
  echo "PHASE1_2_GATE_D_DECISION=REQUIRES_MANUAL_CHECK"
  echo "PHASE1_2_GATE_E_SAFETY=REQUIRES_MANUAL_CHECK"
  echo "PHASE1_2_GATE_F_RESOURCES=SEE_SNAPSHOT_ABOVE"

  if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}Overall: PASS${NC}"
    exit 0
  fi

  echo -e "${RED}Overall: FAIL${NC}"
  exit 1
}

main "$@"
