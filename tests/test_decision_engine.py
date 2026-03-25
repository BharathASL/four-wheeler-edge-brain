import json

from src.llama_adapter import MockLlamaAdapter
from src.state_manager import StateManager
from src.decision_engine import DecisionEngine


def test_decision_rules_stop():
    state = StateManager()
    de = DecisionEngine()
    action = de.decide("Please STOP now", state.snapshot())
    assert action["action"] == "STOP"


def test_decision_rules_estop():
    state = StateManager()
    de = DecisionEngine()
    action = de.decide("emergency stop now", state.snapshot())
    assert action["action"] == "ESTOP"


def test_decision_rules_dock():
    state = StateManager()
    de = DecisionEngine()
    action = de.decide("go charge and dock", state.snapshot())
    assert action["action"] == "DOCK"


def test_decision_model_fallback():
    state = StateManager()
    llama = MockLlamaAdapter()
    llama.load_model("mock")
    de = DecisionEngine(llama_adapter=llama)
    action = de.decide("explore the area", state.snapshot())
    assert action["action"] == "IDLE"
    assert action["params"].get("reason") == "UNKNOWN_COMMAND"
    assert action["params"].get("confirmation_required") is True
