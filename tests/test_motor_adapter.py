import pytest

from src.action_executor import ActionExecutor
from src.motor_adapter import MockMotorAdapter, PWMMotorAdapter
from src.state_manager import StateManager


def test_mock_motor_adapter_records_motion_commands_and_stop():
    adapter = MockMotorAdapter()

    adapter.set_motion(0.25, 30.0)
    adapter.stop()

    assert len(adapter.commands) == 1
    assert adapter.commands[0].linear_mps == 0.25
    assert adapter.commands[0].angular_dps == 30.0
    assert adapter.stop_count == 1


def test_pwm_motor_adapter_requires_backend():
    adapter = PWMMotorAdapter()

    with pytest.raises(RuntimeError, match="not configured"):
        adapter.set_motion(0.1, 0.0)

    with pytest.raises(RuntimeError, match="not configured"):
        adapter.stop()


def test_pwm_motor_adapter_delegates_to_backend_methods():
    events = []

    class _Backend:
        def set_motion(self, linear_mps, angular_dps):
            events.append(("move", linear_mps, angular_dps))

        def stop(self):
            events.append(("stop",))

    adapter = PWMMotorAdapter(backend=_Backend())
    adapter.set_motion(0.2, -15.0)
    adapter.stop()

    assert events == [("move", 0.2, -15.0), ("stop",)]


def test_action_executor_uses_motor_adapter_for_move_and_stop():
    motor = MockMotorAdapter()
    state = StateManager()
    executor = ActionExecutor(hardware_adapters={"motor": motor}, state_manager=state)

    move_result = executor.execute({"action": "MOVE", "params": {"linear_mps": 0.2, "angular_dps": 10.0}})
    stop_result = executor.execute({"action": "STOP", "params": {}})

    assert move_result["status"] == "ok"
    assert move_result["info"] == "moving-adapter"
    assert motor.commands[-1].linear_mps == 0.2
    assert motor.commands[-1].angular_dps == 10.0
    assert stop_result == {"status": "ok", "info": "stopped"}
    assert motor.stop_count == 1


def test_action_executor_stops_motor_when_safety_blocks_move():
    motor = MockMotorAdapter()
    state = StateManager()
    state.update(front_proximity_m=0.1, side_proximity_m=0.1)
    executor = ActionExecutor(hardware_adapters={"motor": motor}, state_manager=state)

    result = executor.execute({"action": "MOVE", "params": {"linear_mps": 0.2, "angular_dps": 0.0}})

    assert result["status"] == "ok"
    assert result["info"] == "stopped-by-safety"
    assert motor.commands == []
    assert motor.stop_count == 1


def test_action_executor_estop_stops_motor_and_allows_followup_stop():
    motor = MockMotorAdapter()
    state = StateManager()
    executor = ActionExecutor(hardware_adapters={"motor": motor}, state_manager=state)

    estop_result = executor.execute({"action": "ESTOP", "params": {}})
    stop_result = executor.execute({"action": "STOP", "params": {}})

    assert estop_result == {"status": "ok", "info": "estop-latched"}
    assert stop_result == {"status": "ok", "info": "stopped"}
    assert motor.stop_count == 2


def test_action_executor_returns_error_when_stop_backend_fails():
    class _BrokenStopMotor:
        def stop(self):
            raise RuntimeError("stop failed")

    state = StateManager()
    executor = ActionExecutor(hardware_adapters={"motor": _BrokenStopMotor()}, state_manager=state)

    result = executor.execute({"action": "STOP", "params": {}})

    assert result["status"] == "error"
    assert result["info"] == "motor-stop-failed"
    assert state.get("estop_latched") is True


def test_action_executor_latches_estop_when_move_backend_fails():
    class _BrokenMoveMotor:
        def __init__(self):
            self.stop_count = 0

        def set_motion(self, linear_mps, angular_dps):
            raise RuntimeError("move failed")

        def stop(self):
            self.stop_count += 1

    motor = _BrokenMoveMotor()
    state = StateManager()
    executor = ActionExecutor(hardware_adapters={"motor": motor}, state_manager=state)

    result = executor.execute({"action": "MOVE", "params": {"linear_mps": 0.2, "angular_dps": 5.0}})

    assert result["status"] == "error"
    assert result["info"] == "motor-adapter-failed"
    assert state.get("estop_latched") is True
    assert state.get("is_idle") is True
    assert motor.stop_count == 1