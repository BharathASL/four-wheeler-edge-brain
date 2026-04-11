"""Thread-safe state manager for the robot's internal state.

Provides a minimal dict-like API with a lock for safe concurrent access.
"""
import time
from threading import Lock
from typing import Any, Dict


class StateManager:
    def __init__(self):
        self._lock = Lock()
        self._state: Dict[str, Any] = {
            "battery_level": 100,
            "is_charging": False,
            "location": None,
            "tasks": [],
            "is_idle": True,
            "estop_latched": False,
            "manual_override": False,
            "last_command_ts": time.time(),
            "watchdog_triggered": False,
            "front_proximity_m": 1.0,
            "side_proximity_m": 1.0,
            "operating_mode": "SAFE_STOP",
        }

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value

    def update(self, **kwargs) -> None:
        with self._lock:
            self._state.update(kwargs)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state)


__all__ = ["StateManager"]
