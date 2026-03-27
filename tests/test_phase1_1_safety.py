import time

from src.action_executor import ActionExecutor
from src.background_tasks import CommandWatchdogTask
from src.state_manager import StateManager


def test_move_is_clamped_to_max_speed():
    state = StateManager()
    executor = ActionExecutor(state_manager=state)
    action = {"action": "MOVE", "params": {"linear_mps": 10.0, "angular_dps": 100.0}}

    result = executor.execute(action)

    assert result["status"] == "ok"
    assert result["info"] == "moving-simulated"
    assert result["params"]["linear_mps"] <= 0.35
    assert result["params"]["angular_dps"] <= 45.0


def test_move_blocked_when_proximity_is_too_close():
    state = StateManager()
    state.update(front_proximity_m=0.1, side_proximity_m=0.1)
    executor = ActionExecutor(state_manager=state)
    action = {"action": "MOVE", "params": {"linear_mps": 0.2, "angular_dps": 0.0}}

    result = executor.execute(action)

    assert result["status"] == "ok"
    assert result["info"] == "stopped-by-safety"


def test_move_stays_simulated_without_motor_adapter():
    state = StateManager()
    executor = ActionExecutor(state_manager=state)

    result = executor.execute({"action": "MOVE", "params": {"linear_mps": 0.2, "angular_dps": 5.0}})

    assert result["status"] == "ok"
    assert result["info"] == "moving-simulated"


def test_estop_latch_blocks_actions_until_reset():
    state = StateManager()
    executor = ActionExecutor(state_manager=state)

    estop_result = executor.execute({"action": "ESTOP", "params": {}})
    blocked_result = executor.execute({"action": "MOVE", "params": {"linear_mps": 0.1}})
    reset_result = executor.execute({"action": "RESET_ESTOP", "params": {}})
    post_reset_result = executor.execute({"action": "MOVE", "params": {"linear_mps": 0.1}})

    assert estop_result["info"] == "estop-latched"
    assert blocked_result["status"] == "blocked"
    assert reset_result["info"] == "estop-reset"
    assert post_reset_result["status"] == "ok"


def test_manual_override_blocks_model_suggestions():
    state = StateManager()
    executor = ActionExecutor(state_manager=state)

    executor.execute({"action": "OVERRIDE_ON", "params": {}})
    result = executor.execute({"action": "MODEL_SUGGESTION", "params": {"text": "move"}})

    assert result["status"] == "blocked"
    assert "manual-override" in result["info"]


def test_watchdog_triggers_stop_action(poll):
    state = StateManager()
    # Simulate stale heartbeat before starting watchdog.
    state.set("last_command_ts", time.time() - 10.0)
    seen = []

    def _on_stop(action):
        seen.append(action)

    task = CommandWatchdogTask(
        state,
        on_watchdog_stop=_on_stop,
        timeout_seconds=0.05,
        tick_seconds=0.01,
    )
    task.start()
    try:
        triggered = poll(lambda: len(seen) > 0)
    finally:
        task.stop()

    assert triggered, "watchdog callback should have fired"
    assert seen[0]["action"] == "STOP"
    assert seen[0]["params"].get("source") == "watchdog"
