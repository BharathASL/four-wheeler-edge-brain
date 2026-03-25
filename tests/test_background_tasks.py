import time

from src.background_tasks import BatteryBackgroundTask
from src.state_manager import StateManager


def test_battery_task_drains_when_not_charging():
    state = StateManager()
    state.update(battery_level=5, is_charging=False)

    task = BatteryBackgroundTask(state, tick_seconds=0.02, drain_step=1, charge_step=1, low_battery_threshold=1)
    task.start()
    time.sleep(0.08)
    task.stop()

    assert state.get("battery_level") < 5


def test_battery_task_triggers_auto_dock_once():
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
    time.sleep(0.1)
    task.stop()

    assert seen
    assert seen[0]["action"] == "DOCK"
    assert state.get("auto_dock_triggered") is True
