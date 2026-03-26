# Phase 1.1 — Safety Hardening Before Mobility

This document defines the Phase-1.1 plan after Phase-1 simulation readiness.

## Goals

- Add movement safety controls before full mobility autonomy.
- Ensure unknown or unsafe commands fail safely.
- Define reliability behavior for STT and model runtime failures.
- Prepare clear operational limits for speed and proximity.

## Scope

- Unknown-command confirmation flow with safe fallback action.
- Safety control limits (max speed and proximity clamps).
- Watchdog timers and manual override behavior.
- Emergency stop behavior (software and hardware interaction model).
- Failure-mode handling for Vosk and llama-cpp.

## Deliverables

- Architecture/tasks checklist: `docs/phase1_1/ARCHITECTURE_TASKS.md`
- Safety and control policy: `docs/phase1_1/SAFETY_AND_CONTROL.md`
- Runtime failure handling policy: `docs/phase1_1/FAILURE_MODES.md`

## Implementation Notes

- Continue using adapter boundaries from Phase-1.
- Keep all Phase-1.1 safety decisions deterministic and testable.
- Enforce "safe by default" behavior in all uncertain states.

---

Last updated: 2026-03-26
