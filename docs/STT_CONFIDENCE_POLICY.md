# STT Confidence Policy

This document defines how speech-to-text confidence is handled in the runtime.

## Configuration

- `STT_CONFIDENCE_THRESHOLD` (default: `0.7`)
  - Accepted range: `0.0` to `1.0` (env values are clamped)
  - A transcript is rejected when `confidence < threshold`
- `STT_REPROMPT_ON_REJECT` (default: `true`)
  - Controls whether the UX re-prompts after a rejection
  - Rejection semantics remain consistent even when re-prompt is disabled

## Runtime Behavior

- `confidence > threshold`: transcript is accepted
- `confidence == threshold`: transcript is accepted (inclusive boundary)
- `confidence < threshold`: transcript is rejected with `STT_LOW_CONFIDENCE`
- `confidence is None`: transcript is accepted by policy

## Fallback Policy

For low-confidence input, the listener reports `STT_LOW_CONFIDENCE` and the loop emits an idle action path rather than executing a command.

- With `STT_REPROMPT_ON_REJECT=true`: reject + re-prompt UX
- With `STT_REPROMPT_ON_REJECT=false`: reject without re-prompt UX

In both modes, command execution is blocked for low-confidence transcripts.
