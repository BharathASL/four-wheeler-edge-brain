def test_smoke_flow():
    from src.adapters.llama_adapter import MockLlamaAdapter
    from src.adapters.audio_adapter import MockAudioAdapter
    from src.adapters.camera_adapter import MockCameraAdapter
    from src.adapters.tts_adapter import MockTTSAdapter
    from src.core.state_manager import StateManager
    from src.core.decision_engine import DecisionEngine
    from src.core.action_executor import ActionExecutor

    # initialize components
    state = StateManager()
    llama = MockLlamaAdapter()
    llama.load_model("mock")
    audio = MockAudioAdapter()
    camera = MockCameraAdapter()
    tts = MockTTSAdapter()

    # basic interactions
    recorded = audio.record(0.1)
    assert recorded
    frame = camera.capture_frame()
    assert frame is not None
    tts.speak("system ready")
    assert tts.spoken_texts[-1] == "system ready"

    de = DecisionEngine(llama_adapter=llama)
    action = de.decide("please dock", state.snapshot())
    assert isinstance(action, dict)

    executor = ActionExecutor()
    result = executor.execute(action)
    assert result.get("status") == "ok"
