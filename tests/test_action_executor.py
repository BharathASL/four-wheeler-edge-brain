from src.core.action_executor import ActionExecutor
from src.core.state_manager import StateManager

def test_action_executor_safe_stop_blocks_all_but_safe_actions():
    state = StateManager()
    state.update(operating_mode="SAFE_STOP")
    executor = ActionExecutor(state_manager=state)

    # Safe actions should pass the block (they may return their own ok/error)
    assert executor.execute({"action": "STOP"}).get("status") == "ok"
    assert executor.execute({"action": "IDLE"}).get("status") == "ok"
    assert executor.execute({"action": "ESTOP"}).get("status") == "ok"

    # Other actions should be blocked
    result = executor.execute({"action": "MOVE", "params": {}})
    assert result["status"] == "blocked"
    assert result["info"] == "safe-stop-mode-active"

    result = executor.execute({"action": "DOCK", "params": {}})
    assert result["status"] == "blocked"
    assert result["info"] == "safe-stop-mode-active"

def test_action_executor_manual_blocks_non_manual_safe_actions():
    state = StateManager()
    state.update(operating_mode="MANUAL")
    executor = ActionExecutor(state_manager=state)

    # Manual safe action
    result = executor.execute({"action": "MOVE", "meta": {"manual_safe": True}, "params": {}})
    assert result["status"] == "ok"
    assert result["info"] == "moving-simulated"

    # Non-manual safe action
    result = executor.execute({"action": "DOCK", "meta": {"manual_safe": False}, "params": {}})
    assert result["status"] == "blocked"
    assert result["info"] == "manual-mode-restricted"

def test_action_executor_autonomous_allows_actions():
    state = StateManager()
    state.update(operating_mode="AUTONOMOUS")
    executor = ActionExecutor(state_manager=state)

    # Both manual safe and non-manual safe actions should be allowed
    result = executor.execute({"action": "MOVE", "meta": {"manual_safe": True}, "params": {}})
    assert result["status"] == "ok"
    assert result["info"] == "moving-simulated"

    result = executor.execute({"action": "DOCK", "meta": {"manual_safe": False}, "params": {}})
    assert result["status"] == "ok"
    assert result["info"] == "docking-simulated"
