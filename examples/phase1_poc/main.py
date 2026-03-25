"""Small Phase-1 PoC entrypoint.

Run `python examples/phase1_poc/main.py test` to run the test-suite, or run
without args to start a tiny simulated loop.
"""
import sys
import time
from queue import Empty, Queue

from src.telemetry import init_telemetry


def run_tests():
    import pytest

    sys.exit(pytest.main(["-q"]))


def _build_tts(enabled: bool):
    if not enabled:
        return None

    from src.tts_adapter import Pyttsx3TTSAdapter

    return Pyttsx3TTSAdapter()


def simulate_loop(enable_tts: bool = False):
    from src.background_tasks import BatteryBackgroundTask, CommandWatchdogTask
    from src.state_manager import StateManager
    from src.input_listener import ConsoleInputListener
    from src.llama_adapter import MockLlamaAdapter
    from src.decision_engine import DecisionEngine
    from src.action_executor import ActionExecutor

    logger = init_telemetry("phase1_poc")
    state = StateManager()
    llama = MockLlamaAdapter()
    llama.load_model("mock")
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


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("test", "tests"):
        run_tests()
    else:
        enable_tts = "--tts" in sys.argv
        simulate_loop(enable_tts=enable_tts)


if __name__ == "__main__":
    main()
