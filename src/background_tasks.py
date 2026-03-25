"""Background task helpers for Phase-1 simulation.

Includes a battery monitor loop that simulates battery drain/charge and triggers
an auto-dock callback when battery drops below a threshold.
"""
import threading
import time
from typing import Callable, Dict, Any, Optional


class BatteryBackgroundTask:
    """Simulate battery drain and trigger auto-dock on low battery."""

    def __init__(
        self,
        state_manager,
        on_auto_dock: Optional[Callable[[Dict[str, Any]], None]] = None,
        tick_seconds: float = 1.0,
        drain_step: int = 1,
        charge_step: int = 2,
        low_battery_threshold: int = 20,
    ):
        self.state = state_manager
        self.on_auto_dock = on_auto_dock
        self.tick_seconds = tick_seconds
        self.drain_step = drain_step
        self.charge_step = charge_step
        self.low_battery_threshold = low_battery_threshold

        self._stop = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="battery-task", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            snap = self.state.snapshot()
            level = int(snap.get("battery_level", 100))
            is_charging = bool(snap.get("is_charging", False))
            auto_dock_triggered = bool(snap.get("auto_dock_triggered", False))

            if is_charging:
                level = min(100, level + self.charge_step)
                if level >= 100:
                    # Simulate charging complete and release the auto-dock latch.
                    self.state.update(battery_level=level, is_charging=False, auto_dock_triggered=False)
                else:
                    self.state.set("battery_level", level)
            else:
                level = max(0, level - self.drain_step)
                self.state.set("battery_level", level)

                if level <= self.low_battery_threshold and not auto_dock_triggered:
                    self.state.set("auto_dock_triggered", True)
                    if self.on_auto_dock is not None:
                        self.on_auto_dock(
                            {
                                "action": "DOCK",
                                "params": {
                                    "source": "battery_monitor",
                                    "battery_level": level,
                                },
                            }
                        )

            time.sleep(self.tick_seconds)


class CommandWatchdogTask:
    """Monitor command heartbeat and trigger STOP on timeout."""

    def __init__(
        self,
        state_manager,
        on_watchdog_stop: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout_seconds: float = 2.0,
        tick_seconds: float = 0.2,
    ):
        self.state = state_manager
        self.on_watchdog_stop = on_watchdog_stop
        self.timeout_seconds = timeout_seconds
        self.tick_seconds = tick_seconds

        self._stop = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="watchdog-task", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            snap = self.state.snapshot()
            last_command_ts = float(snap.get("last_command_ts", time.time()))
            timed_out = (time.time() - last_command_ts) > self.timeout_seconds
            watchdog_triggered = bool(snap.get("watchdog_triggered", False))

            if timed_out and not watchdog_triggered:
                self.state.set("watchdog_triggered", True)
                if self.on_watchdog_stop is not None:
                    self.on_watchdog_stop(
                        {
                            "action": "STOP",
                            "params": {
                                "source": "watchdog",
                                "reason": "COMMAND_TIMEOUT",
                            },
                        }
                    )
            elif not timed_out and watchdog_triggered:
                # Heartbeat recovered; clear latch.
                self.state.set("watchdog_triggered", False)

            time.sleep(self.tick_seconds)


__all__ = ["BatteryBackgroundTask", "CommandWatchdogTask"]
