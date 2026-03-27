"""Decision Engine: rules-first with optional model fallback.

This module exposes a `DecisionEngine` class that accepts input text and
returns a structured ACTION dict. The implementation below is intentionally
minimal for Phase‑1 and suitable for unit testing with mocked adapters.
"""
from typing import Dict, Any

from src.chat_behavior import sanitize_user_facing_reply
from src.config import RobotConfig as _cfg
from src.input_sanitizer import sanitize_for_model_prompt
from src.model_rate_limiter import ModelRateLimiter


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
        3. Always return a dict with `action` and optional `params`.
        """
        text = user_input.strip().lower()

        if not text:
            return {"action": "IDLE", "params": {"reason": "EMPTY_COMMAND"}}

        # Rule: emergency stop takes highest priority.
        if any(k in text for k in ("e-stop", "estop", "emergency stop", "emergency", "hard stop")):
            return {"action": "ESTOP", "params": {"reason": "USER_REQUEST"}}

        if "reset estop" in text or "reset emergency" in text:
            return {"action": "RESET_ESTOP", "params": {}}

        if any(k in text for k in ("stop", "halt")):
            return {"action": "STOP", "params": {}}

        if "override on" in text:
            return {"action": "OVERRIDE_ON", "params": {}}
        if "override off" in text:
            return {"action": "OVERRIDE_OFF", "params": {}}

        # Rule: battery
        if "charge" in text or "dock" in text:
            return {"action": "DOCK", "params": {}}

        # Rule: basic movement intents (will be safety-clamped by executor).
        if "forward" in text:
            return {"action": "MOVE", "params": {"linear_mps": _cfg.DEFAULT_FWD_SPEED_MPS, "angular_dps": 0.0}}
        if "back" in text or "reverse" in text:
            return {"action": "MOVE", "params": {"linear_mps": _cfg.DEFAULT_BACK_SPEED_MPS, "angular_dps": 0.0}}
        if "left" in text:
            return {"action": "MOVE", "params": {"linear_mps": 0.0, "angular_dps": _cfg.DEFAULT_TURN_LEFT_DPS}}
        if "right" in text:
            return {"action": "MOVE", "params": {"linear_mps": 0.0, "angular_dps": _cfg.DEFAULT_TURN_RIGHT_DPS}}

        # Model fallback
        if self.llama is not None:
            allowed, retry_after = self.model_rate_limiter.allow()
            if not allowed:
                return {
                    "action": "IDLE",
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
                    "params": {
                        "reason": "UNKNOWN_COMMAND",
                        "confirmation_required": True,
                        "model_hint": model_hint,
                    },
                }
            except TimeoutError:
                return {"action": "IDLE", "params": {"reason": "MODEL_TIMEOUT", "confirmation_required": True}}
            except RuntimeError:
                # Runtime (native lib missing) — fall back to IDLE so tests/dev don't crash
                return {"action": "IDLE", "params": {"reason": "MODEL_UNAVAILABLE", "confirmation_required": True}}
            except Exception:
                return {"action": "IDLE", "params": {"reason": "MODEL_ERROR", "confirmation_required": True}}

        # Default: unknowns are safe-idle with explicit confirmation requirement.
        return {"action": "IDLE", "params": {"reason": "UNKNOWN_COMMAND", "confirmation_required": True}}


__all__ = ["DecisionEngine"]
