"""Action Executor: execute or simulate hardware actions.

Provides a small `ActionExecutor` that calls hardware adapter stubs. For Phase-1
the executor logs and returns simulated results.
"""
from typing import Dict, Any

from src.safety_controller import clamp_movement_action


class ActionExecutor:
    def __init__(self, hardware_adapters: Dict[str, Any] = None, state_manager=None):
        self.adapters = hardware_adapters or {}
        self.state = state_manager

    def _state_snapshot(self) -> Dict[str, Any]:
        if self.state is None:
            return {}
        return self.state.snapshot()

    def _state_update(self, **kwargs) -> None:
        if self.state is not None:
            self.state.update(**kwargs)

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a structured `action` (dict with `action` and `params`).

        Returns a result dict with `status` and optional `info`.
        """
        name = action.get("action")
        params = action.get("params", {})
        snap = self._state_snapshot()

        if name == "ESTOP":
            self._state_update(estop_latched=True, is_idle=True)
            return {"status": "ok", "info": "estop-latched"}

        if name == "RESET_ESTOP":
            if snap.get("estop_latched"):
                self._state_update(estop_latched=False)
                return {"status": "ok", "info": "estop-reset"}
            return {"status": "ok", "info": "estop-not-active"}

        if snap.get("estop_latched"):
            return {"status": "blocked", "info": "estop-latched"}

        if name == "OVERRIDE_ON":
            self._state_update(manual_override=True)
            return {"status": "ok", "info": "manual-override-on"}
        if name == "OVERRIDE_OFF":
            self._state_update(manual_override=False)
            return {"status": "ok", "info": "manual-override-off"}

        if snap.get("manual_override") and name in ("MODEL_SUGGESTION",):
            return {"status": "blocked", "info": "manual-override-active"}

        # Simulation-mode actions
        if name == "STOP":
            return {"status": "ok", "info": "stopped"}
        if name == "IDLE":
            self._state_update(is_idle=True)
            return {"status": "ok", "info": "idle"}
        if name == "DOCK":
            return {"status": "ok", "info": "docking-simulated"}
        if name == "MOVE":
            safe_action = clamp_movement_action(action, snap)
            if safe_action.get("action") == "STOP":
                return {"status": "ok", "info": "stopped-by-safety", "safety": safe_action.get("params", {})}
            safe_params = safe_action.get("params", {})
            return {
                "status": "ok",
                "info": "moving-simulated",
                "params": {
                    "linear_mps": safe_params.get("linear_mps", 0.0),
                    "angular_dps": safe_params.get("angular_dps", 0.0),
                },
            }
        if name == "MODEL_SUGGESTION":
            return {"status": "ok", "info": params.get("text")}

        return {"status": "unknown-action", "info": name}


__all__ = ["ActionExecutor"]
