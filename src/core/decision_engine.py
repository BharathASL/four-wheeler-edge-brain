"""Decision Engine: rules-first with optional model fallback.

This module exposes a `DecisionEngine` class that accepts input text and
returns a structured ACTION dict. The implementation below is intentionally
minimal for Phase‑1 and suitable for unit testing with mocked adapters.
"""
from typing import Dict, Any

from src.io.chat_behavior import sanitize_user_facing_reply, classify_intent
from src.config import RobotConfig as _cfg
from src.io.input_sanitizer import sanitize_for_model_prompt
from src.core.model_rate_limiter import ModelRateLimiter


class DecisionEngine:
    def __init__(
        self,
        llama_adapter=None,
        model_timeout: float = _cfg.MODEL_TIMEOUT_S,
        model_rate_limiter: ModelRateLimiter | None = None,
    ):
        self.llama = llama_adapter
        self.model_timeout = model_timeout
        self.model_rate_limiter = model_rate_limiter or ModelRateLimiter(0.0)

    def decide(self, user_input: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Return a structured ACTION dict.

        Strategy:
        1. Apply simple rules for urgent or safety commands.
        2. If no rule matches and a model is available, call model for suggestion.
        3. Always return a dict with `action`, optional `params` (for compatibility),
           and normalized `goal` / `meta` schema for the Autonomy mode.
        """
        text = user_input.strip().lower()

        if not text:
            return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "EMPTY_COMMAND"}}

        # Rule: emergency stop takes highest priority.
        if any(k in text for k in ("e-stop", "estop", "emergency stop", "emergency", "hard stop")):
            return {"action": "ESTOP", "goal": {"type": "estop"}, "meta": {"manual_safe": True}, "params": {"reason": "USER_REQUEST"}}

        if "reset estop" in text or "reset emergency" in text:
            return {"action": "RESET_ESTOP", "goal": {"type": "reset_estop"}, "meta": {"manual_safe": True}, "params": {}}

        if any(k in text for k in ("stop", "halt")):
            return {"action": "STOP", "goal": {"type": "stop"}, "meta": {"manual_safe": True}, "params": {}}

        if "override on" in text:
            return {"action": "OVERRIDE_ON", "goal": {"type": "override_on"}, "meta": {"manual_safe": True}, "params": {}}
        if "override off" in text:
            return {"action": "OVERRIDE_OFF", "goal": {"type": "override_off"}, "meta": {"manual_safe": True}, "params": {}}

        intent = classify_intent(text)

        if intent == "MOTION_GOAL":
            state["last_was_ambiguous"] = False
            if "go to" in text:
                target = text.split("go to", 1)[1].strip()
                if target:
                    return {"action": "MOVE", "goal": {"type": "go_to_location", "target": target}, "meta": {"manual_safe": False}, "params": {}}
                # Fall through to ambiguous flow if empty target
                intent = "AMBIGUOUS"
            elif "come to me" in text or "follow" in text:
                return {"action": "MOVE", "goal": {"type": "follow_person", "target": "nearest_person"}, "meta": {"manual_safe": False}, "params": {}}
            elif "patrol" in text:
                return {"action": "MOVE", "goal": {"type": "patrol", "zone": "current_area"}, "meta": {"manual_safe": False}, "params": {}}
            elif "dock" in text or "charge" in text:
                return {"action": "DOCK", "goal": {"type": "dock"}, "meta": {"manual_safe": False}, "params": {}}
            elif "forward" in text:
                return {"action": "MOVE", "goal": {"type": "move", "direction": "forward"}, "meta": {"manual_safe": True}, "params": {"linear_mps": _cfg.DEFAULT_FWD_SPEED_MPS, "angular_dps": 0.0}}
            elif "back" in text or "reverse" in text:
                return {"action": "MOVE", "goal": {"type": "move", "direction": "backward"}, "meta": {"manual_safe": True}, "params": {"linear_mps": _cfg.DEFAULT_BACK_SPEED_MPS, "angular_dps": 0.0}}
            elif "left" in text:
                return {"action": "MOVE", "goal": {"type": "move", "direction": "left"}, "meta": {"manual_safe": True}, "params": {"linear_mps": 0.0, "angular_dps": _cfg.DEFAULT_TURN_LEFT_DPS}}
            elif "right" in text:
                return {"action": "MOVE", "goal": {"type": "move", "direction": "right"}, "meta": {"manual_safe": True}, "params": {"linear_mps": 0.0, "angular_dps": _cfg.DEFAULT_TURN_RIGHT_DPS}}

        if intent == "AMBIGUOUS":
            if state.get("last_was_ambiguous", False):
                state["last_was_ambiguous"] = False
                return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "AMBIGUOUS_FALLBACK", "confirmation_required": True}}
            else:
                state["last_was_ambiguous"] = True
                return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "UNKNOWN_COMMAND", "confirmation_required": True, "model_hint": "Could you clarify what you mean?"}}

        state["last_was_ambiguous"] = False

        # Model fallback
        if self.llama is not None:
            allowed, retry_after = self.model_rate_limiter.allow()
            if not allowed:
                return {
                    "action": "IDLE",
                    "goal": {"type": "idle"},
                    "meta": {"manual_safe": True},
                    "params": {
                        "reason": "MODEL_COOLDOWN",
                        "confirmation_required": True,
                        "retry_after_s": round(retry_after, 2),
                    },
                }
            safe_input = sanitize_for_model_prompt(user_input)
            prompt = f"Decide action for input: {safe_input}\nState: {state}\nReturn JSON with action and params."
            try:
                resp = self.llama.generate(prompt, max_tokens=128, timeout=self.model_timeout)
                if not isinstance(resp, str) or not resp.strip():
                    return {
                        "action": "IDLE",
                        "goal": {"type": "idle"},
                        "meta": {"manual_safe": True},
                        "params": {
                            "reason": "MODEL_MALFORMED_OUTPUT",
                            "confirmation_required": True,
                        },
                    }
                model_hint = sanitize_user_facing_reply(
                    user_input,
                    resp,
                    fallback="I did not understand that command well enough to act safely.",
                )
                # Unknown command path: ask for confirmation and stay safe/idle.
                return {
                    "action": "IDLE",
                    "goal": {"type": "idle"},
                    "meta": {"manual_safe": True},
                    "params": {
                        "reason": "UNKNOWN_COMMAND",
                        "confirmation_required": True,
                        "model_hint": model_hint,
                    },
                }
            except TimeoutError:
                return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "MODEL_TIMEOUT", "confirmation_required": True}}
            except RuntimeError:
                # Runtime (native lib missing) — fall back to IDLE so tests/dev don't crash
                return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "MODEL_UNAVAILABLE", "confirmation_required": True}}
            except Exception:
                return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "MODEL_ERROR", "confirmation_required": True}}

        # Default: unknowns are safe-idle with explicit confirmation requirement.
        return {"action": "IDLE", "goal": {"type": "idle"}, "meta": {"manual_safe": True}, "params": {"reason": "UNKNOWN_COMMAND", "confirmation_required": True}}


__all__ = ["DecisionEngine"]
