# Phase 1.1 — Runtime Failure Modes (Vosk + llama-cpp)

This document defines failure handling and retry behavior for speech input and model inference.

## 1) Vosk Failure Modes + Retries

### Common Failure Modes

- Microphone not available / busy
- Device permission errors
- Partial transcripts with low confidence
- Empty transcript for non-silent input
- Decoder runtime exception

### Retry and Fallback Policy

- `STT_MAX_RETRIES = 2`
- `STT_RETRY_BACKOFF_MS = 300`

Policy:

1. On transient failure, retry up to max retries.
2. On repeated failure, emit safe fallback command intent:

```json
{
  "action": "IDLE",
  "params": {
    "reason": "STT_UNAVAILABLE",
    "confirmation_required": true
  }
}
```

3. Prompt user for typed input fallback where possible.
4. Log all retry attempts and terminal failure.

## 2) llama-cpp Failure Modes + Timeouts

### Common Failure Modes

- Runtime library unavailable (`llama.cpp`/binding load failure)
- Model file missing or invalid path
- Inference timeout
- OOM during model load/inference
- Invalid/unparseable model output

### Timeout and Retry Policy

- `MODEL_TIMEOUT_SECONDS = 5.0`
- `MODEL_MAX_RETRIES = 1`

Policy:

1. Enforce per-request timeout.
2. Retry once for timeout or transient runtime errors.
3. On terminal failure, return deterministic safe fallback:

```json
{
  "action": "IDLE",
  "params": {
    "reason": "MODEL_UNAVAILABLE",
    "confirmation_required": true
  }
}
```

4. Never execute movement actions directly from unvalidated model text.
5. Route model output through command-to-action validation and safety clamps.

## 3) Failure Severity Levels

- `INFO`: transient retry succeeded
- `WARN`: retry exhausted, safe fallback applied
- `ERROR`: unrecoverable runtime failure
- `CRITICAL`: safety-related compounded failures requiring `STOP`

## 4) Observability Requirements

Each failure record should include:

- component (`vosk` or `llama-cpp`)
- error category
- retry count
- timeout value (if applicable)
- applied fallback action

## 5) Safe-by-Default Rule

When confidence is low or runtime health is uncertain:

1. prefer `IDLE`
2. request confirmation
3. avoid movement actions without explicit validated intent

---

Last updated: 2026-03-26
