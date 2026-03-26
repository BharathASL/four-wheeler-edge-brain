# Phase 1.1 — Safety & Control Policy

This document defines Phase-1.1 safety behavior for mobility-related decision and execution layers.

## 1) Unknown-Command Confirmation Flow

When a command cannot be mapped to a known safe action:

1. Emit `ACTION:IDLE` immediately.
2. Ask for explicit confirmation or rephrase.
3. Retry command mapping only after confirmation input.
4. If confirmation is missing/unclear, remain in `IDLE`.

Required output shape for unknown command:

```json
{
  "action": "IDLE",
  "params": {
    "reason": "UNKNOWN_COMMAND",
    "confirmation_required": true
  }
}
```

## 2) Max Speed & Proximity Clamps

Safety clamps must apply before any movement action is executed.

- `MAX_LINEAR_SPEED_MPS = 0.35`
- `MAX_ANGULAR_SPEED_DPS = 45`
- `MIN_FRONT_PROXIMITY_M = 0.35`
- `MIN_SIDE_PROXIMITY_M = 0.20`

Clamp rules:

1. If desired speed exceeds max, reduce to max.
2. If proximity is below minimum, block forward movement and return `STOP`.

## 3) Watchdog Timer Policy

Use watchdogs to detect control-loop stalls or stale command channels.

- `CONTROL_LOOP_WATCHDOG_MS = 1500`
- `COMMAND_HEARTBEAT_TIMEOUT_MS = 2000`

Behavior on watchdog timeout:

1. Preempt current action.
2. Emit `STOP`.
3. Transition to safe `IDLE` until healthy heartbeat resumes.

## 4) Manual Override Policy

Manual override always has higher priority than autonomous behavior.

- Sources: physical switch, keyboard command, remote control channel.
- Activation command example: `override on`
- Deactivation command example: `override off`

Rules:

1. On activation, cancel all autonomous queued actions.
2. Accept only manual control actions until override is disabled.
3. Log every override state transition.

## 5) Emergency Stop Behavior

Emergency stop is highest-priority safety action.

Triggers:

- Explicit command: `stop`, `emergency stop`, `e-stop`
- Hardware e-stop signal
- Critical safety fault (watchdog + hazard condition)

Behavior:

1. Immediately issue motor stop command.
2. Clear pending action queue.
3. Latch system in `ESTOP_LATCHED` state.
4. Require explicit reset command before movement resumes.

State transition notes:

- `RUNNING -> ESTOP_LATCHED`
- `ESTOP_LATCHED -> IDLE` only after explicit reset + health checks pass

## 6) Logging Requirements

The system must log these events with timestamp and reason:

- Unknown-command fallback events
- Clamp activations
- Watchdog timeouts
- Manual override toggles
- E-stop trigger and reset

---

Last updated: 2026-03-26
