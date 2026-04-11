"""Action Executor: execute or simulate hardware actions.

Provides a small `ActionExecutor` that calls hardware adapter stubs. For Phase-1
the executor logs and returns simulated results.
"""
from typing import Dict, Any

from src.core.safety_controller import clamp_movement_action


class ActionExecutor:
    def __init__(self, hardware_adapters: Dict[str, Any] = None, state_manager=None):
        self.adapters = hardware_adapters or {}
        self.state = state_manager

    def _motor_adapter(self):
        return self.adapters.get("motor")

    def _stop_motor_safely(self, error_info: str):
        motor = self._motor_adapter()
        if motor is None:
            return None
        try:
            motor.stop()
            return None
        except Exception as exc:
            self._state_update(estop_latched=True, is_idle=True)
            return {
                "status": "error",
                "info": error_info,
                "error": str(exc),
            }

    def _fail_safe_motor_error(self, info: str, exc: Exception):
        self._state_update(estop_latched=True, is_idle=True)
        stop_error = self._stop_motor_safely(error_info=f"{info}-stop-failed")
        result = {
            "status": "error",
            "info": info,
            "error": str(exc),
        }
        if stop_error is not None:
            result["stop_error"] = stop_error["error"]
        return result

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
        meta = action.get("meta", {})
        snap = self._state_snapshot()
        mode = snap.get("operating_mode", "SAFE_STOP")

        if mode == "SAFE_STOP" and name not in ("STOP", "ESTOP", "RESET_ESTOP", "IDLE"):
            return {"status": "blocked", "info": "safe-stop-mode-active"}

        if mode == "MANUAL" and not meta.get("manual_safe") and name not in ("STOP", "ESTOP", "RESET_ESTOP", "IDLE"):
            return {"status": "blocked", "info": "manual-mode-restricted"}

        if name == "STOP":
            stop_error = self._stop_motor_safely(error_info="motor-stop-failed")
            if stop_error is not None:
                return stop_error
            return {"status": "ok", "info": "stopped"}

        if name == "ESTOP":
            self._state_update(estop_latched=True, is_idle=True)
            stop_error = self._stop_motor_safely(error_info="estop-stop-failed")
            if stop_error is not None:
                return stop_error
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
        if name == "IDLE":
            self._state_update(is_idle=True)
            return {"status": "ok", "info": "idle"}
        if name == "DOCK":
            return {"status": "ok", "info": "docking-simulated"}
        if name == "MOVE":
            safe_action = clamp_movement_action(action, snap)
            if safe_action.get("action") == "STOP":
                stop_error = self._stop_motor_safely(error_info="motor-stop-failed")
                if stop_error is not None:
                    return stop_error
                return {"status": "ok", "info": "stopped-by-safety", "safety": safe_action.get("params", {})}
            safe_params = safe_action.get("params", {})
            motor = self._motor_adapter()
            if motor is not None:
                try:
                    motor.set_motion(
                        linear_mps=safe_params.get("linear_mps", 0.0),
                        angular_dps=safe_params.get("angular_dps", 0.0),
                    )
                except Exception as exc:
                    return self._fail_safe_motor_error("motor-adapter-failed", exc)
                return {
                    "status": "ok",
                    "info": "moving-adapter",
                    "params": {
                        "linear_mps": safe_params.get("linear_mps", 0.0),
                        "angular_dps": safe_params.get("angular_dps", 0.0),
                    },
                }
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
