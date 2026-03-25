def test_smoke_flow():
    from src.llama_adapter import MockLlamaAdapter
    from src.audio_adapter import MockAudioAdapter
    from src.camera_adapter import MockCameraAdapter
    from src.tts_adapter import MockTTSAdapter
    from src.state_manager import StateManager
    from src.decision_engine import DecisionEngine
    from src.action_executor import ActionExecutor

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
