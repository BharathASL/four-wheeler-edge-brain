from main import process_listener_once
from src.core.action_executor import ActionExecutor
from src.core.decision_engine import DecisionEngine
from src.core.state_manager import StateManager


class _SequenceListener:
    def __init__(self, commands):
        self._commands = list(commands)

    def poll_once(self):
        if not self._commands:
            return None
        return self._commands.pop(0)

    def take_error(self):
        return None


class _FailingSpeechListener:
    def __init__(self, error):
        self.error = error

    def poll_once(self):
        return None

    def take_error(self):
        if self.error is None:
            return None
        error = self.error
        self.error = None
        return error


def test_process_listener_once_runs_full_command_loop():
    state = StateManager()
    state.update(operating_mode="AUTONOMOUS")
    decision_engine = DecisionEngine()
    executor = ActionExecutor(state_manager=state)
    listener = _SequenceListener(["go charge and dock"])

    outcome = process_listener_once(listener, state, decision_engine, executor)

    assert outcome is not None
    assert outcome["input"] == "go charge and dock"
    assert outcome["action"]["action"] == "DOCK"
    assert outcome["result"]["status"] == "ok"
    assert outcome["result"]["info"] == "docking-simulated"
    assert state.get("is_charging") is True
    assert state.get("is_idle") is True


def test_process_listener_once_converts_stt_failure_to_safe_idle():
    state = StateManager()
    state.update(operating_mode="AUTONOMOUS")
    decision_engine = DecisionEngine()
    executor = ActionExecutor(state_manager=state)
    listener = _FailingSpeechListener("STT_UNAVAILABLE")

    outcome = process_listener_once(listener, state, decision_engine, executor)

    assert outcome is not None
    assert outcome["error"] == "STT_UNAVAILABLE"
    assert outcome["action"]["action"] == "IDLE"
    assert outcome["action"]["params"]["reason"] == "STT_UNAVAILABLE"
    assert outcome["result"]["status"] == "ok"
    assert outcome["result"]["info"] == "idle"
    assert state.get("is_idle") is True


def test_process_listener_once_preserves_exit_command():
    state = StateManager()
    state.update(operating_mode="AUTONOMOUS")
    decision_engine = DecisionEngine()
    executor = ActionExecutor(state_manager=state)
    listener = _SequenceListener(["exit"])

    outcome = process_listener_once(listener, state, decision_engine, executor)

    assert outcome == {"input": "exit", "exit": True}