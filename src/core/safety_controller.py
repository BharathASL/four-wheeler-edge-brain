"""Safety controls for command execution.

This module centralizes movement clamps and proximity checks so action execution
can enforce deterministic safety rules.
"""
from typing import Any, Dict

from src.config import RobotConfig as _cfg

MAX_LINEAR_SPEED_MPS = _cfg.MAX_LINEAR_SPEED_MPS
MAX_ANGULAR_SPEED_DPS = _cfg.MAX_ANGULAR_SPEED_DPS
MIN_FRONT_PROXIMITY_M = _cfg.MIN_FRONT_PROXIMITY_M
MIN_SIDE_PROXIMITY_M = _cfg.MIN_SIDE_PROXIMITY_M


def clamp_movement_action(action: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a safe action after applying speed and proximity constraints."""
    if action.get("action") != "MOVE":
        return action

    params = dict(action.get("params", {}))
    linear = float(params.get("linear_mps", 0.0))
    angular = float(params.get("angular_dps", 0.0))
    front = float(params.get("front_proximity_m", state.get("front_proximity_m", 1.0)))
    side = float(params.get("side_proximity_m", state.get("side_proximity_m", 1.0)))

    # Do not allow forward motion when minimum distance is violated.
    if linear > 0 and (front < MIN_FRONT_PROXIMITY_M or side < MIN_SIDE_PROXIMITY_M):
        return {
            "action": "STOP",
            "params": {
                "reason": "PROXIMITY_BLOCK",
                "front_proximity_m": front,
                "side_proximity_m": side,
            },
        }

    clamped_linear = max(-MAX_LINEAR_SPEED_MPS, min(MAX_LINEAR_SPEED_MPS, linear))
    clamped_angular = max(-MAX_ANGULAR_SPEED_DPS, min(MAX_ANGULAR_SPEED_DPS, angular))
    params.update({"linear_mps": clamped_linear, "angular_dps": clamped_angular})

    return {"action": "MOVE", "params": params}


__all__ = [
    "MAX_LINEAR_SPEED_MPS",
    "MAX_ANGULAR_SPEED_DPS",
    "MIN_FRONT_PROXIMITY_M",
    "MIN_SIDE_PROXIMITY_M",
    "clamp_movement_action",
]
