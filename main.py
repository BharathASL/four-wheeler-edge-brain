"""Root entrypoint for the Phase-1 PoC runtime.

Run `python main.py test` to run the test-suite, or run without args to start
the simulated runtime loop.
"""
import os
import sys
import time
from pathlib import Path
from queue import Empty, Queue

# Ensure repository root is on sys.path when running via absolute path.
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.telemetry import init_telemetry


def run_tests():
    import pytest

    sys.exit(pytest.main(["-q"]))


def _build_tts(enabled: bool):
    if not enabled:
        return None

    from src.tts_adapter import Pyttsx3TTSAdapter

    return Pyttsx3TTSAdapter()


def _build_llama_adapter(model_mode: str, model_path: str, lib_path: str, strict_model: bool, logger):
    from src.llama_adapter import LlamaAdapter, MockLlamaAdapter

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


def simulate_loop(
    enable_tts: bool = False,
    model_mode: str = "mock",
    model_path: str = "",
    llama_lib_path: str = "",
    strict_model: bool = False,
):
    from src.background_tasks import BatteryBackgroundTask, CommandWatchdogTask
    from src.state_manager import StateManager
    from src.input_listener import ConsoleInputListener
    from src.decision_engine import DecisionEngine
    from src.action_executor import ActionExecutor

    logger = init_telemetry("phase1_poc")
    state = StateManager()
    llama, effective_mode = _build_llama_adapter(
        model_mode=model_mode,
        model_path=model_path,
        lib_path=llama_lib_path,
        strict_model=strict_model,
        logger=logger,
    )
    listener = ConsoleInputListener(prompt="> ")
    de = DecisionEngine(llama_adapter=llama)
    execer = ActionExecutor(state_manager=state)
    tts = None
    auto_actions = Queue()

    def enqueue_auto_action(action):
        auto_actions.put(action)

    battery_task = BatteryBackgroundTask(
        state,
        on_auto_dock=enqueue_auto_action,
        tick_seconds=1.0,
        drain_step=1,
        charge_step=2,
        low_battery_threshold=20,
    )
    watchdog_task = CommandWatchdogTask(
        state,
        on_watchdog_stop=enqueue_auto_action,
        timeout_seconds=60.0,
        tick_seconds=0.5,
    )

    try:
        tts = _build_tts(enable_tts)
    except RuntimeError as exc:
        logger.warning("TTS disabled: %s", exc)

    print("Starting Phase-1 PoC simulation (Ctrl-C to stop)")
    print(f"Model mode: requested={model_mode} active={effective_mode}")
    if enable_tts and tts is None:
        print("TTS requested but unavailable; running without speech")
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
            user = listener.poll_once()
            if not user:
                continue
            state.set("last_command_ts", time.time())
            if user.lower() in ("quit", "exit"):
                print("exit command received")
                break
            action = de.decide(user, state.snapshot())
            result = execer.execute(action)
            if action.get("action") == "DOCK":
                state.update(is_charging=True, is_idle=True)
            print("Action:", action)
            print("Result:", result)
            logger.info("action=%s result=%s", action, result)

            if tts is not None:
                if result.get("info"):
                    tts.speak(str(result.get("info")))
                else:
                    tts.speak(str(action.get("action", "NO_OP")))
    except KeyboardInterrupt:
        print("exiting")
    finally:
        battery_task.stop()
        watchdog_task.stop()


def chat_loop(
    model_mode: str = "mock",
    model_path: str = "",
    llama_lib_path: str = "",
    strict_model: bool = False,
    max_tokens: int = 128,
    history_turns: int = 4,
    memory_db_path: str = "data/conversations.sqlite",
):
    from src.conversation_memory import ConversationMemoryStore

    def _clean_chat_reply(text: str) -> str:
        cleaned = (text or "").strip()
        for marker in ("\nUser:", "\nuser:", "User:", "user:"):
            if marker in cleaned:
                cleaned = cleaned.split(marker, 1)[0].strip()
        return cleaned

    def _identify_speaker(store: ConversationMemoryStore):
        while True:
            speaker_name = input("speaker> Who is speaking? ").strip()
            if not speaker_name:
                print("Please enter a non-empty speaker name")
                continue
            speaker_id, is_new = store.get_or_create_user(speaker_name)
            if is_new:
                print(f"New speaker profile created for: {speaker_name}")
            else:
                print(f"Welcome back: {speaker_name}")
            return speaker_id, speaker_name

    logger = init_telemetry("phase1_chat")
    memory_store = ConversationMemoryStore(db_path=memory_db_path)
    llama, effective_mode = _build_llama_adapter(
        model_mode=model_mode,
        model_path=model_path,
        lib_path=llama_lib_path,
        strict_model=strict_model,
        logger=logger,
    )
    speaker_id, speaker_name = _identify_speaker(memory_store)

    print("Starting chat mode (Ctrl-C to stop)")
    print(f"Model mode: requested={model_mode} active={effective_mode}")
    print("Type 'quit' or 'exit' to stop")
    print("Type '/switch' to switch speaker profile")
    print(f"Chat history window: last {history_turns} turns")

    try:
        while True:
            user = input("chat> ").strip()
            if not user:
                continue
            if user.lower() in ("quit", "exit"):
                print("exit command received")
                break
            if user.lower() == "/switch":
                speaker_id, speaker_name = _identify_speaker(memory_store)
                continue

            recent = memory_store.get_recent_turns(speaker_id, limit=history_turns)
            history_lines = [
                "You are an offline robot assistant.",
                "Reply briefly and clearly.",
                f"Current speaker name: {speaker_name}",
                "Use prior turns for continuity when they are relevant.",
            ]
            for turn in recent:
                history_lines.append(f"User: {turn['user']}")
                history_lines.append(f"Assistant: {turn['assistant']}")
            history_lines.append(f"User: {user}")
            history_lines.append("Assistant:")
            prompt = "\n".join(history_lines)

            try:
                reply = llama.generate(prompt, max_tokens=max_tokens, timeout=20)
                cleaned_reply = _clean_chat_reply(reply) or "[empty response]"
                print("assistant>", cleaned_reply)
                memory_store.append_turn(speaker_id, user, cleaned_reply)
            except Exception as exc:
                logger.exception("chat_generation_failed")
                print(f"assistant> [error] {exc}")
    except KeyboardInterrupt:
        print("exiting")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("test", "tests"):
        run_tests()
    else:
        enable_tts = "--tts" in sys.argv
        strict_model = "--strict-model" in sys.argv
        chat_mode = "--chat-mode" in sys.argv

        env_mode = os.getenv("MODEL_MODE", "mock")
        env_model_path = os.getenv("MODEL_PATH", "")
        env_lib_path = os.getenv("LLAMA_LIB_PATH", "")
        env_memory_db_path = os.getenv("MEMORY_DB_PATH", "data/conversations.sqlite")

        cli_mode = env_mode
        cli_model_path = env_model_path
        cli_lib_path = env_lib_path
        cli_history_turns = 4
        cli_memory_db_path = env_memory_db_path

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
            if token == "--memory-db-path" and idx + 1 < len(sys.argv):
                cli_memory_db_path = sys.argv[idx + 1]

        if chat_mode:
            chat_loop(
                model_mode=cli_mode,
                model_path=cli_model_path,
                llama_lib_path=cli_lib_path,
                strict_model=strict_model,
                history_turns=cli_history_turns,
                memory_db_path=cli_memory_db_path,
            )
            return

        simulate_loop(
            enable_tts=enable_tts,
            model_mode=cli_mode,
            model_path=cli_model_path,
            llama_lib_path=cli_lib_path,
            strict_model=strict_model,
        )


if __name__ == "__main__":
    main()
