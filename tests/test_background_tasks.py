import time

from src.core.background_tasks import BatteryBackgroundTask
from src.core.state_manager import StateManager


def test_battery_task_drains_when_not_charging(poll):
    state = StateManager()
    state.update(battery_level=5, is_charging=False)

    task = BatteryBackgroundTask(state, tick_seconds=0.02, drain_step=1, charge_step=1, low_battery_threshold=1)
    task.start()
    try:
        drained = poll(lambda: state.get("battery_level") < 5)
    finally:
        task.stop()

    assert drained, "battery level should have decreased"


def test_battery_task_triggers_auto_dock_once(poll):
    state = StateManager()
    state.update(battery_level=3, is_charging=False, auto_dock_triggered=False)
    seen = []

    def on_auto_dock(action):
        seen.append(action)

    task = BatteryBackgroundTask(
        state,
        on_auto_dock=on_auto_dock,
        tick_seconds=0.02,
        drain_step=1,
        charge_step=1,
        low_battery_threshold=2,
    )
    task.start()
    try:
        triggered = poll(lambda: len(seen) > 0)
    finally:
        task.stop()

    assert triggered, "auto-dock callback should have fired"
    assert seen[0]["action"] == "DOCK"
    assert state.get("auto_dock_triggered") is True
