"""Shared cooldown guard for model-backed operations."""

from __future__ import annotations

import threading
import time
from typing import Callable


class ModelRateLimiter:
    def __init__(self, cooldown_seconds: float = 0.0, time_fn: Callable[[], float] | None = None):
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._time_fn = time_fn or time.monotonic
        self._lock = threading.Lock()
        self._last_model_call_ts = 0.0

    def allow(self) -> tuple[bool, float]:
        if self.cooldown_seconds <= 0:
            return True, 0.0

        with self._lock:
            now = self._time_fn()
            elapsed = now - self._last_model_call_ts
            if self._last_model_call_ts > 0.0 and elapsed < self.cooldown_seconds:
                return False, max(0.0, self.cooldown_seconds - elapsed)
            self._last_model_call_ts = now
            return True, 0.0


__all__ = ["ModelRateLimiter"]