"""Root entrypoint for the Phase-1 PoC runtime.

Run `python main.py test` to run the test-suite, or run without args to start
the simulated runtime loop.
"""
import sys
import time
from pathlib import Path
from queue import Empty, Queue

# Ensure repository root is on sys.path when running via absolute path.
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import RobotConfig
from src.telemetry import init_telemetry


def run_tests():
    import pytest

    sys.exit(pytest.main(["-q"]))


def _print_exit_loading() -> None:
    print()
    print("exiting", end="", flush=True)
    for _ in range(3):
        time.sleep(0.25)
        print(".", end="", flush=True)
    print()


def _build_tts(enabled: bool):
    if not enabled:
        return None

    from src.adapters.tts_adapter import Pyttsx3TTSAdapter

    return Pyttsx3TTSAdapter()


def _build_llama_adapter(model_mode: str, model_path: str, lib_path: str, strict_model: bool, logger):
    from src.adapters.llama_adapter import LlamaAdapter, MockLlamaAdapter

    requested_mode = (model_mode or "mock").strip().lower()
    if requested_mode not in ("mock", "real"):
        logger.warning("Unknown MODEL_MODE=%s; falling back to mock", requested_mode)
        requested_mode = "mock"

    if requested_mode == "mock":
        llama = MockLlamaAdapter()
        llama.load_model("mock")
        return llama, "mock"

    if not model_path:
        message = "MODEL_PATH is required for MODEL_MODE=real"
        if strict_model:
            raise RuntimeError(message)
        logger.warning("%s; falling back to mock", message)
        llama = MockLlamaAdapter()
        llama.load_model("mock")
        return llama, "mock"

    llama = LlamaAdapter(lib_path=lib_path or None)
    llama.load_model(model_path)
    # LlamaAdapter may fail softly and keep runtime unavailable; allow fallback.
    if getattr(llama, "_llm", None) is None:
        message = "llama runtime unavailable in real mode"
        if strict_model:
            raise RuntimeError(message)
        logger.warning("%s; falling back to mock", message)
        mock = MockLlamaAdapter()
        mock.load_model("mock")
        return mock, "mock"

    return llama, "real"


def _build_input_listener(
    stt_mode: str,
    vosk_model_path: str,
    cfg: RobotConfig,
    logger,
):
    from src.io.input_listener import ConsoleInputListener, SpeechInputListener

    mode = (stt_mode or "console").strip().lower()
    if mode == "console":
        return ConsoleInputListener(prompt="> "), "console"

    if mode == "vosk":
        try:
            from src.adapters.audio_adapter import SoundDeviceAudioAdapter, StreamingVADAudioAdapter, VoskSpeechToTextAdapter
            from src.adapters.audio_preprocessor import AudioPreprocessor

            if cfg.AUDIO_VAD_STREAM_ENABLED:
                audio_adapter = StreamingVADAudioAdapter(
                    sample_rate_hz=cfg.STT_SAMPLE_RATE_HZ,
                    aggressiveness=cfg.AUDIO_VAD_AGGRESSIVENESS,
                    chunk_ms=cfg.AUDIO_VAD_CHUNK_MS,
                    silence_padding_ms=cfg.AUDIO_VAD_SILENCE_PADDING_MS,
                    max_duration_s=cfg.AUDIO_VAD_MAX_DURATION_S,
                    min_speech_ms=cfg.AUDIO_VAD_MIN_SPEECH_MS,
                    speech_energy_gate_dbfs=cfg.AUDIO_VAD_SPEECH_GATE_DBFS,
                )
                logger.info(
                    "audio_vad_stream enabled=True aggressiveness=%d chunk_ms=%d padding_ms=%d max_s=%s min_speech_ms=%d speech_gate_dbfs=%s",
                    cfg.AUDIO_VAD_AGGRESSIVENESS,
                    cfg.AUDIO_VAD_CHUNK_MS,
                    cfg.AUDIO_VAD_SILENCE_PADDING_MS,
                    cfg.AUDIO_VAD_MAX_DURATION_S,
                    cfg.AUDIO_VAD_MIN_SPEECH_MS,
                    cfg.AUDIO_VAD_SPEECH_GATE_DBFS,
                )
            else:
                audio_adapter = SoundDeviceAudioAdapter(sample_rate_hz=cfg.STT_SAMPLE_RATE_HZ, channels=1)
            stt_adapter = VoskSpeechToTextAdapter(
                model_path=vosk_model_path,
                sample_rate_hz=cfg.STT_SAMPLE_RATE_HZ,
                max_retries=cfg.STT_MAX_RETRIES,
                retry_backoff_s=cfg.STT_RETRY_BACKOFF_S,
            )
            preprocessor = AudioPreprocessor(cfg) if cfg.AUDIO_PREPROCESS_ENABLED else None
            logger.info(
                "audio_preprocess enabled=%s noise_gate=%s vad=%s agc=%s",
                cfg.AUDIO_PREPROCESS_ENABLED,
                cfg.AUDIO_NOISE_GATE_ENABLED,
                cfg.AUDIO_VAD_ENABLED,
                cfg.AUDIO_AGC_ENABLED,
            )
            listener = SpeechInputListener(
                audio_adapter=audio_adapter,
                stt_adapter=stt_adapter,
                duration=cfg.AUDIO_RECORD_DURATION_S,
                confidence_threshold=cfg.STT_CONFIDENCE_THRESHOLD,
                reprompt_on_reject=cfg.STT_REPROMPT_ON_REJECT,
                preprocessor=preprocessor,
            )
            return listener, "vosk"
        except Exception as exc:
            logger.warning("STT mode 'vosk' unavailable (%s); falling back to console", exc)
            return ConsoleInputListener(prompt="> "), "console"

    logger.warning("Unknown STT mode=%s; falling back to console", stt_mode)
    return ConsoleInputListener(prompt="> "), "console"


def process_command_text(user_input, state, decision_engine, executor):
    if not user_input:
        return None

    state.set("last_command_ts", time.time())
    action = decision_engine.decide(user_input, state.snapshot())
    result = executor.execute(action)
    if action.get("action") == "DOCK":
        state.update(is_charging=True, is_idle=True)
    return {"input": user_input, "action": action, "result": result}


def process_listener_once(listener, state, decision_engine, executor):
    user_input = listener.poll_once()
    listener_error = listener.take_error()

    if listener_error:
        # Special handling for low confidence: treat as no-op, optionally notify user
        if listener_error == "STT_LOW_CONFIDENCE":
            action = {
                "action": "IDLE",
                "params": {
                    "reason": "Low STT confidence",
                    "confirmation_required": False,
                },
            }
            result = executor.execute(action)
            return {"input": None, "action": action, "result": result, "error": listener_error}
        else:
            action = {
                "action": "IDLE",
                "params": {
                    "reason": listener_error,
                    "confirmation_required": True,
                },
            }
            result = executor.execute(action)
            return {"input": None, "action": action, "result": result, "error": listener_error}

    if not user_input:
        return None

    if user_input.lower() in ("quit", "exit"):
        return {"input": user_input, "exit": True}

    return process_command_text(user_input, state, decision_engine, executor)


def simulate_loop(
    enable_tts: bool = False,
    model_mode: str = "mock",
    model_path: str = "",
    llama_lib_path: str = "",
    strict_model: bool = False,
    http_api_enabled: bool = False,
    http_api_host: str = "127.0.0.1",
    http_api_port: int = 8080,
    stt_mode: str = "console",
    vosk_model_path: str = "",
    cfg: RobotConfig | None = None,
):
    from src.core.background_tasks import BatteryBackgroundTask, CommandWatchdogTask
    from src.core.state_manager import StateManager
    from src.core.decision_engine import DecisionEngine
    from src.api.http_api import HttpApiServer
    from src.core.model_rate_limiter import ModelRateLimiter
    from src.core.action_executor import ActionExecutor

    if cfg is None:
        cfg = RobotConfig.from_env()
    logger = init_telemetry("phase1_poc", cfg=cfg)
    model_cooldown_seconds = max(0.0, cfg.MODEL_COOLDOWN_S)
    state = StateManager()
    llama, effective_mode = _build_llama_adapter(
        model_mode=model_mode,
        model_path=model_path,
        lib_path=llama_lib_path,
        strict_model=strict_model,
        logger=logger,
    )
    listener, effective_stt_mode = _build_input_listener(
        stt_mode=stt_mode,
        vosk_model_path=vosk_model_path,
        cfg=cfg,
        logger=logger,
    )
    de = DecisionEngine(
        llama_adapter=llama,
        model_rate_limiter=ModelRateLimiter(model_cooldown_seconds),
    )
    execer = ActionExecutor(state_manager=state)
    tts = None
    api_server = None
    auto_actions = Queue()

    def enqueue_auto_action(action):
        auto_actions.put(action)

    battery_task = BatteryBackgroundTask(
        state,
        on_auto_dock=enqueue_auto_action,
    )
    watchdog_task = CommandWatchdogTask(
        state,
        on_watchdog_stop=enqueue_auto_action,
    )

    try:
        tts = _build_tts(enable_tts)
    except RuntimeError as exc:
        logger.warning("TTS disabled: %s", exc)

    print("Starting Phase-1 PoC simulation (Ctrl-C to stop)")
    print(f"Model mode: requested={model_mode} active={effective_mode}")
    print(f"Input mode: requested={stt_mode} active={effective_stt_mode}")
    if enable_tts and tts is None:
        print("TTS requested but unavailable; running without speech")

    if http_api_enabled:
        def _api_handle_command_text(command: str):
            return process_command_text(command, state, de, execer)

        api_server = HttpApiServer(
            host=http_api_host,
            port=http_api_port,
            get_state=state.snapshot,
            handle_command_text=_api_handle_command_text,
            mode=effective_mode,
        )
        api_server.start()
        print(f"HTTP API stub listening on http://{http_api_host}:{api_server.bound_port}")

    battery_task.start()
    watchdog_task.start()
    print("Background battery task started (auto-dock <= 20%)")

    try:
        while True:
            while True:
                try:
                    auto_action = auto_actions.get_nowait()
                except Empty:
                    break

                result = execer.execute(auto_action)
                if auto_action.get("action") == "DOCK":
                    state.update(is_charging=True, is_idle=True)
                print("Auto Action:", auto_action)
                print("Auto Result:", result)
                logger.info("auto_action=%s result=%s", auto_action, result)
                if tts is not None:
                    tts.speak("Auto dock triggered")

            print(f"Battery: {state.get('battery_level')}% | Charging: {state.get('is_charging')}")
            outcome = process_listener_once(listener, state, de, execer)
            if outcome is None:
                continue
            if outcome.get("exit"):
                print("exit command received")
                break
            action = outcome["action"]
            result = outcome["result"]
            if outcome.get("error"):
                print("Input Error:", outcome["error"])
            if outcome.get("input"):
                confidence = listener.get_last_confidence() if hasattr(listener, 'get_last_confidence') else None
                conf_str = f" (confidence: {confidence:.2f})" if confidence is not None else ""
                print(f"🎤 You said: '{outcome['input']}'{conf_str}")
            print("Action:", action)
            print("Result:", result)
            logger.info("action=%s result=%s", action, result)

            if tts is not None:
                if result.get("info"):
                    tts.speak(str(result.get("info")))
                else:
                    tts.speak(str(action.get("action", "NO_OP")))
    except KeyboardInterrupt:
        _print_exit_loading()
    finally:
        if api_server is not None:
            api_server.stop()
        battery_task.stop()
        watchdog_task.stop()


def chat_loop(
    model_mode: str = "mock",
    model_path: str = "",
    llama_lib_path: str = "",
    strict_model: bool = False,
    max_tokens: int = 128,
    history_turns: int = 4,
    retrieval_turns: int = 3,
    benchmark_memory_retrieval: bool = False,
    memory_db_path: str = "data/conversations.sqlite",
    retrieval_mode: str = "fts",
    semantic_backend: str = "auto",
    cfg: RobotConfig | None = None,
):
    from src.io.chat_behavior import (
        MODEL_COOLDOWN_REPLY,
        dedupe_relevant_turns,
        effective_retrieval_limit,
        generate_chat_reply_with_source,
        identify_speaker,
        normalize_personal_fact_for_storage,
    )
    from src.memory.conversation_memory import ConversationMemoryStore, RetrievalBenchmarkRecorder
    from src.core.model_rate_limiter import ModelRateLimiter
    from src.memory.semantic_memory import SemanticMemoryIndex

    if cfg is None:
        cfg = RobotConfig.from_env()
    logger = init_telemetry("phase1_chat", cfg=cfg)
    model_cooldown_seconds = max(0.0, cfg.MODEL_COOLDOWN_S)
    normalized_retrieval_mode = (retrieval_mode or "fts").strip().lower()
    if normalized_retrieval_mode not in {"fts", "semantic", "hybrid"}:
        logger.warning("Unknown retrieval mode=%s; falling back to fts", retrieval_mode)
        normalized_retrieval_mode = "fts"

    normalized_semantic_backend = (semantic_backend or "auto").strip().lower()
    semantic_index = None
    if normalized_retrieval_mode in {"semantic", "hybrid"}:
        prefer_faiss = normalized_semantic_backend != "in-memory"
        semantic_index = SemanticMemoryIndex(prefer_faiss=prefer_faiss)

    memory_store = ConversationMemoryStore(
        db_path=memory_db_path,
        semantic_index=semantic_index,
        default_retrieval_mode=normalized_retrieval_mode,
    )
    retrieval_bench = RetrievalBenchmarkRecorder() if benchmark_memory_retrieval else None
    model_rate_limiter = ModelRateLimiter(model_cooldown_seconds)
    llama, effective_mode = _build_llama_adapter(
        model_mode=model_mode,
        model_path=model_path,
        lib_path=llama_lib_path,
        strict_model=strict_model,
        logger=logger,
    )
    speaker_id, speaker_name = identify_speaker(memory_store)

    print("Starting chat mode (Ctrl-C to stop)")
    print(f"Model mode: requested={model_mode} active={effective_mode}")
    print("Type 'quit' or 'exit' to stop")
    print("Type '/switch' to switch speaker profile")
    print(f"Chat history window: last {history_turns} turns")
    print(f"Long-memory retrieval window: top {retrieval_turns} turns")
    print(f"Retrieval mode: {normalized_retrieval_mode}")
    if semantic_index is not None:
        print(f"Semantic backend: {semantic_index.backend_name}")
    print(f"Model cooldown window: {model_cooldown_seconds:.1f}s")
    if retrieval_bench is not None:
        print("Memory retrieval benchmark hooks: enabled")

    try:
        while True:
            user = input("chat> ").strip()
            if not user:
                continue
            if user.lower() in ("quit", "exit"):
                print("exit command received")
                break
            if user.lower() == "/switch":
                speaker_id, speaker_name = identify_speaker(memory_store)
                continue

            recent = memory_store.get_recent_turns(speaker_id, limit=history_turns)
            effective_retrieval_turns = effective_retrieval_limit(user, retrieval_turns)
            relevant_old = memory_store.search_relevant_turns(
                user_id=speaker_id,
                query=user,
                limit=effective_retrieval_turns,
                metrics_hook=retrieval_bench.record if retrieval_bench is not None else None,
                retrieval_mode=normalized_retrieval_mode,
            )
            relevant_old = dedupe_relevant_turns(recent, relevant_old)
            saved_slots = memory_store.get_all_slots(speaker_id)

            try:
                cleaned_reply, reply_source = generate_chat_reply_with_source(
                    llama,
                    user,
                    speaker_name,
                    recent,
                    relevant_old,
                    max_tokens=max_tokens,
                    model_rate_limiter=model_rate_limiter,
                    memory_slots=saved_slots,
                )
                print(f"assistant[{reply_source}]>", cleaned_reply)
                if cleaned_reply != MODEL_COOLDOWN_REPLY:
                    memory_store.append_turn(speaker_id, normalize_personal_fact_for_storage(user), cleaned_reply)
            except Exception as exc:
                logger.exception("chat_generation_failed")
                print(f"assistant> [error] {exc}")
    except KeyboardInterrupt:
        _print_exit_loading()
    finally:
        if retrieval_bench is not None:
            summary = retrieval_bench.summary()
            print(
                "Memory retrieval metrics:",
                (
                    f"queries={int(summary['queries'])} "
                    f"avg_ms={summary['avg_latency_ms']:.2f} "
                    f"max_ms={summary['max_latency_ms']:.2f} "
                    f"avg_hits={summary['avg_returned_count']:.2f} "
                    f"fts_ratio={summary['fts_usage_ratio']:.2f}"
                ),
            )


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("test", "tests"):
        run_tests()
    else:
        enable_tts = "--tts" in sys.argv
        strict_model = "--strict-model" in sys.argv
        chat_mode = "--chat-mode" in sys.argv

        cfg = RobotConfig.from_env()

        cli_mode = cfg.MODEL_MODE
        cli_model_path = cfg.MODEL_PATH
        cli_lib_path = cfg.LLAMA_LIB_PATH
        cli_history_turns = cfg.CHAT_HISTORY_TURNS
        cli_retrieval_turns = cfg.RETRIEVAL_TURNS
        cli_benchmark_memory_retrieval = False
        cli_memory_db_path = cfg.MEMORY_DB_PATH
        cli_retrieval_mode = cfg.MEMORY_RETRIEVAL_MODE
        cli_semantic_backend = cfg.SEMANTIC_BACKEND
        cli_http_api_enabled = cfg.HTTP_API_ENABLED
        cli_http_api_host = cfg.HTTP_API_HOST
        cli_http_api_port = cfg.HTTP_API_PORT
        cli_stt_mode = cfg.STT_MODE
        cli_vosk_model_path = cfg.VOSK_MODEL_PATH

        for idx, token in enumerate(sys.argv):
            if token == "--model-mode" and idx + 1 < len(sys.argv):
                cli_mode = sys.argv[idx + 1]
            if token == "--model-path" and idx + 1 < len(sys.argv):
                cli_model_path = sys.argv[idx + 1]
            if token == "--llama-lib-path" and idx + 1 < len(sys.argv):
                cli_lib_path = sys.argv[idx + 1]
            if token == "--chat-history-turns" and idx + 1 < len(sys.argv):
                try:
                    cli_history_turns = max(0, int(sys.argv[idx + 1]))
                except ValueError:
                    print("Invalid --chat-history-turns value; defaulting to 4")
                    cli_history_turns = 4
            if token == "--retrieval-turns" and idx + 1 < len(sys.argv):
                try:
                    cli_retrieval_turns = max(0, int(sys.argv[idx + 1]))
                except ValueError:
                    print("Invalid --retrieval-turns value; defaulting to 3")
                    cli_retrieval_turns = 3
            if token == "--memory-db-path" and idx + 1 < len(sys.argv):
                cli_memory_db_path = sys.argv[idx + 1]
            if token == "--retrieval-mode" and idx + 1 < len(sys.argv):
                cli_retrieval_mode = sys.argv[idx + 1]
            if token == "--semantic-backend" and idx + 1 < len(sys.argv):
                cli_semantic_backend = sys.argv[idx + 1]
            if token == "--http-host" and idx + 1 < len(sys.argv):
                cli_http_api_host = sys.argv[idx + 1]
            if token == "--http-port" and idx + 1 < len(sys.argv):
                try:
                    cli_http_api_port = max(1, int(sys.argv[idx + 1]))
                except ValueError:
                    print("Invalid --http-port value; defaulting to 8080")
                    cli_http_api_port = 8080
            if token == "--stt-mode" and idx + 1 < len(sys.argv):
                cli_stt_mode = sys.argv[idx + 1]
            if token == "--vosk-model-path" and idx + 1 < len(sys.argv):
                cli_vosk_model_path = sys.argv[idx + 1]
        if "--benchmark-memory-retrieval" in sys.argv:
            cli_benchmark_memory_retrieval = True
        if "--http-api" in sys.argv:
            cli_http_api_enabled = True

        if chat_mode:
            chat_loop(
                model_mode=cli_mode,
                model_path=cli_model_path,
                llama_lib_path=cli_lib_path,
                strict_model=strict_model,
                history_turns=cli_history_turns,
                retrieval_turns=cli_retrieval_turns,
                benchmark_memory_retrieval=cli_benchmark_memory_retrieval,
                memory_db_path=cli_memory_db_path,
                retrieval_mode=cli_retrieval_mode,
                semantic_backend=cli_semantic_backend,
                cfg=cfg,
            )
            return

        simulate_loop(
            enable_tts=enable_tts,
            model_mode=cli_mode,
            model_path=cli_model_path,
            llama_lib_path=cli_lib_path,
            strict_model=strict_model,
            http_api_enabled=cli_http_api_enabled,
            http_api_host=cli_http_api_host,
            http_api_port=cli_http_api_port,
            stt_mode=cli_stt_mode,
            vosk_model_path=cli_vosk_model_path,
            cfg=cfg,
        )


if __name__ == "__main__":
    main()
