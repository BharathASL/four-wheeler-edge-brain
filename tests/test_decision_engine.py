import json

from src.llama_adapter import MockLlamaAdapter
from src.state_manager import StateManager
from src.decision_engine import DecisionEngine


class _TimeoutLlama:
    def generate(self, prompt, max_tokens=128, timeout=None):
        raise TimeoutError("timed out")


class _UnavailableLlama:
    def generate(self, prompt, max_tokens=128, timeout=None):
        raise RuntimeError("runtime missing")


class _BrokenLlama:
    def generate(self, prompt, max_tokens=128, timeout=None):
        raise ValueError("bad output")


class _MalformedLlama:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt, max_tokens=128, timeout=None):
        return self.response


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


def test_decision_model_timeout_falls_back_to_safe_idle():
    state = StateManager()
    de = DecisionEngine(llama_adapter=_TimeoutLlama())

    action = de.decide("explore the area", state.snapshot())

    assert action["action"] == "IDLE"
    assert action["params"]["reason"] == "MODEL_TIMEOUT"
    assert action["params"]["confirmation_required"] is True


def test_decision_model_unavailable_falls_back_to_safe_idle():
    state = StateManager()
    de = DecisionEngine(llama_adapter=_UnavailableLlama())

    action = de.decide("explore the area", state.snapshot())

    assert action["action"] == "IDLE"
    assert action["params"]["reason"] == "MODEL_UNAVAILABLE"
    assert action["params"]["confirmation_required"] is True


def test_decision_model_error_falls_back_to_safe_idle():
    state = StateManager()
    de = DecisionEngine(llama_adapter=_BrokenLlama())

    action = de.decide("explore the area", state.snapshot())

    assert action["action"] == "IDLE"
    assert action["params"]["reason"] == "MODEL_ERROR"
    assert action["params"]["confirmation_required"] is True


def test_decision_model_malformed_output_falls_back_to_safe_idle():
    state = StateManager()
    de = DecisionEngine(llama_adapter=_MalformedLlama(None))

    action = de.decide("explore the area", state.snapshot())

    assert action["action"] == "IDLE"
    assert action["params"]["reason"] == "MODEL_MALFORMED_OUTPUT"
    assert action["params"]["confirmation_required"] is True


def test_decision_model_blank_output_falls_back_to_safe_idle():
    state = StateManager()
    de = DecisionEngine(llama_adapter=_MalformedLlama("   "))

    action = de.decide("explore the area", state.snapshot())

    assert action["action"] == "IDLE"
    assert action["params"]["reason"] == "MODEL_MALFORMED_OUTPUT"
    assert action["params"]["confirmation_required"] is True
