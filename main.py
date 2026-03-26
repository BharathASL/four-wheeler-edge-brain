"""Root entrypoint for the Phase-1 PoC runtime.

Run `python main.py test` to run the test-suite, or run without args to start
the simulated runtime loop.
"""
import os
import re
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
    retrieval_turns: int = 3,
    benchmark_memory_retrieval: bool = False,
    memory_db_path: str = "data/conversations.sqlite",
):
    from src.conversation_memory import ConversationMemoryStore, RetrievalBenchmarkRecorder

    def _clean_chat_reply(text: str) -> str:
        cleaned = (text or "").strip()
        lower = cleaned.lower()

        # Strip common role-token fragments emitted by some chat templates.
        for prefix in ("assistant:", "assistant", "<|assistant|>", "answer:", "answer"):
            if lower.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip(" :-\n\t")
                lower = cleaned.lower()

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

    def _is_question(text: str) -> bool:
        lowered = (text or "").strip().lower()
        if not lowered:
            return False
        if lowered.endswith("?"):
            return True
        return lowered.startswith(("what", "why", "how", "when", "where", "who", "do", "did", "are", "can"))

    def _trim_snippet(text: str, max_chars: int = 140) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3] + "..."

    def _extract_known_facts(recent_turns, relevant_turns, limit: int = 4):
        seen = set()
        facts = []
        for turn in recent_turns + relevant_turns:
            candidate = str(turn.get("user", "")).strip()
            if not candidate:
                continue
            if candidate.endswith("?"):
                # Skip question-like entries when building profile facts.
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            facts.append(_trim_snippet(candidate, max_chars=100))
            if len(facts) >= limit:
                break
        return facts

    def _deterministic_personal_response(user_text: str, speaker: str, facts):
        text = user_text.lower()
        asks_name = (
            "my name" in text
            or "who am i" in text
            or "who i am" in text
            or "tell my name" in text
        )
        asks_profile = (
            "what do you know about me" in text
            or "know about me" in text
            or "met before" in text
            or "have we met" in text
            or "remember me" in text
            or "remeber me" in text
        )

        if asks_name:
            return f"Your name is {speaker}."

        if asks_profile:
            if not facts:
                return f"You are {speaker}. I do not have additional verified facts yet."
            summarized = "; ".join(facts[:3])
            return f"You are {speaker}. From our prior conversation: {summarized}."

        return ""

    def _extract_meal_fact(turn_texts, meal_name: str):
        patterns = (
            rf"\bi\s+had\s+(.+?)\s+for\s+{meal_name}\b",
            rf"\bhad\s+(.+?)\s+for\s+{meal_name}\b",
            rf"\bfor\s+{meal_name}\s+i\s+had\s+(.+?)\b",
        )

        for text in reversed(turn_texts):
            candidate = " ".join(str(text or "").strip().split())
            if not candidate:
                continue
            lowered = candidate.lower()
            for pat in patterns:
                match = re.search(pat, lowered)
                if not match:
                    continue
                meal_value = match.group(1).strip(" .,!?:;-")
                if meal_value:
                    return meal_value
        return ""

    def _deterministic_meal_memory_response(user_text: str, speaker: str, recent_turns, relevant_turns):
        lowered = (user_text or "").lower()
        if "had for" not in lowered and "for the" not in lowered and "for dinner" not in lowered:
            return ""

        asked_meal = ""
        for meal in ("dinner", "lunch", "breakfast"):
            if meal in lowered:
                asked_meal = meal
                break
        if not asked_meal:
            return ""

        turn_texts = [turn.get("user", "") for turn in recent_turns + relevant_turns]
        meal_fact = _extract_meal_fact(turn_texts, asked_meal)
        if meal_fact:
            return f"You said you had {meal_fact} for {asked_meal}."

        return (
            f"I remember you as {speaker}, but I do not have your {asked_meal} detail saved yet. "
            "Tell me once and I will remember it for next time."
        )

    def _is_memory_question(user_text: str) -> bool:
        text = (user_text or "").strip().lower()
        if not text:
            return False
        return (
            "remember" in text
            or "remeber" in text
            or "what did i" in text
            or "what do you know about me" in text
            or "know about me" in text
            or "had for" in text
        )

    def _token_set(text: str):
        cleaned = []
        for ch in (text or "").lower():
            cleaned.append(ch if ch.isalnum() or ch.isspace() else " ")
        words = [w for w in "".join(cleaned).split() if len(w) >= 3]
        stop = {
            "what",
            "when",
            "where",
            "which",
            "this",
            "that",
            "have",
            "with",
            "from",
            "your",
            "about",
            "remember",
            "remeber",
            "know",
        }
        return {w for w in words if w not in stop}

    def _memory_confidence(user_text: str, facts):
        if not facts:
            return "low"
        q_tokens = _token_set(user_text)
        if not q_tokens:
            return "medium"

        overlaps = []
        for fact in facts:
            f_tokens = _token_set(fact)
            overlaps.append(len(q_tokens.intersection(f_tokens)))

        best = max(overlaps) if overlaps else 0
        if best >= 2:
            return "high"
        if best == 1:
            return "medium"
        return "low"

    def _memory_question_response(user_text: str, speaker: str, facts):
        if not facts:
            return (
                f"I remember you as {speaker}, but I do not have that detail saved yet. "
                "Tell me once and I will remember it for next time."
            )

        confidence = _memory_confidence(user_text, facts)
        top_fact = facts[0]
        if confidence == "high":
            return f"From what I remember: {top_fact}"
        if confidence == "medium":
            return f"I think this is what you mentioned: {top_fact}"
        return (
            f"I remember you as {speaker}, but I am not confident about that detail yet. "
            "If you share it once, I will store it and recall it later."
        )

    def _is_low_information_reply(text: str) -> bool:
        normalized = " ".join((text or "").strip().lower().split())
        if not normalized:
            return True
        if "empty response" in normalized:
            return True
        if normalized.startswith(("assist", "assistant", "<|assistant|>")):
            return True
        weak = {
            "memory",
            "ok",
            "okay",
            "noted",
            "i see",
            "yes",
            "no",
        }
        if normalized in weak:
            return True
        if len(normalized.split()) <= 2 and len(normalized) <= 14:
            return True
        return False

    def _is_unhelpful_memory_reply(text: str) -> bool:
        normalized = " ".join((text or "").strip().lower().split())
        if not normalized:
            return True
        patterns = (
            "i do not have any memories",
            "i don't have any memories",
            "i have no memories",
            "no memories",
            "i do not remember",
            "i don't remember",
        )
        return any(p in normalized for p in patterns)

    def _grounded_fallback_reply(user_text: str, speaker: str, facts):
        if _is_memory_question(user_text):
            return _memory_question_response(user_text, speaker, facts)

        if _is_question(user_text):
            if facts:
                return f"From what I remember: {facts[0]}"
            return f"I remember you as {speaker}, but I need a bit more detail to answer reliably."

        return f"Got it, {speaker}. I have noted: {_trim_snippet(user_text, max_chars=120)}"

    logger = init_telemetry("phase1_chat")
    memory_store = ConversationMemoryStore(db_path=memory_db_path)
    retrieval_bench = RetrievalBenchmarkRecorder() if benchmark_memory_retrieval else None
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
    print(f"Long-memory retrieval window: top {retrieval_turns} turns")
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
                speaker_id, speaker_name = _identify_speaker(memory_store)
                continue

            recent = memory_store.get_recent_turns(speaker_id, limit=history_turns)
            effective_retrieval_turns = retrieval_turns
            if _is_memory_question(user):
                # Memory lookups are sensitive to ranking noise; widen recall window.
                effective_retrieval_turns = max(retrieval_turns, 3)
            relevant_old = memory_store.search_relevant_turns(
                user_id=speaker_id,
                query=user,
                limit=effective_retrieval_turns,
                metrics_hook=retrieval_bench.record if retrieval_bench is not None else None,
            )

            recent_pairs = {(turn["user"], turn["assistant"]) for turn in recent}
            relevant_old = [
                turn for turn in relevant_old if (turn["user"], turn["assistant"]) not in recent_pairs
            ]

            known_facts = _extract_known_facts(recent, relevant_old)
            deterministic_meal = _deterministic_meal_memory_response(
                user,
                speaker_name,
                recent,
                relevant_old,
            )
            if deterministic_meal:
                print("assistant>", deterministic_meal)
                memory_store.append_turn(speaker_id, user, deterministic_meal)
                continue

            deterministic = _deterministic_personal_response(user, speaker_name, known_facts)
            if deterministic:
                print("assistant>", deterministic)
                memory_store.append_turn(speaker_id, user, deterministic)
                continue

            system_lines = [
                "You are an offline robot assistant.",
                "Reply briefly and clearly.",
                "Use only the provided speaker profile and memory snippets for personal facts.",
                "If a personal fact is unknown in memory, explicitly say you do not know.",
                "Do not invent biography details.",
                f"Current speaker name: {speaker_name}",
            ]

            user_lines = []

            if relevant_old:
                user_lines.append("Relevant older memory snippets:")
                for turn in relevant_old:
                    user_lines.append(f"Memory User: {_trim_snippet(turn['user'])}")
                    user_lines.append(f"Memory Assistant: {_trim_snippet(turn['assistant'])}")

            user_lines.append("Recent conversation:")
            for turn in recent:
                user_lines.append(f"User: {_trim_snippet(turn['user'])}")
                user_lines.append(f"Assistant: {_trim_snippet(turn['assistant'])}")
            user_lines.append(f"Current user message: {user}")

            messages = [
                {"role": "system", "content": "\n".join(system_lines)},
                {"role": "user", "content": "\n".join(user_lines)},
            ]

            try:
                if hasattr(llama, "generate_chat"):
                    reply = llama.generate_chat(messages, max_tokens=max_tokens, timeout=20)
                else:
                    # Compatibility fallback for adapters that only implement `generate`.
                    prompt = (
                        "System:\n"
                        + "\n".join(system_lines)
                        + "\n\nUser:\n"
                        + "\n".join(user_lines)
                        + "\nAssistant:"
                    )
                    reply = llama.generate(prompt, max_tokens=max_tokens, timeout=20)
                cleaned_reply = _clean_chat_reply(reply) or "[empty response]"

                if _is_low_information_reply(cleaned_reply):
                    # One-shot retry with compact grounding to reduce empty/role-fragment outputs.
                    compact_messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are an offline robot assistant. "
                                "Answer in one short sentence. "
                                "Use only provided memory facts for personal questions."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Speaker: {speaker_name}\n"
                                f"Known facts: {('; '.join(known_facts[:2]) if known_facts else 'none')}\n"
                                f"Question: {user}"
                            ),
                        },
                    ]
                    if hasattr(llama, "generate_chat"):
                        retry_reply = llama.generate_chat(compact_messages, max_tokens=min(80, max_tokens), timeout=12)
                    else:
                        retry_prompt = (
                            "System: You are an offline robot assistant. Answer in one short sentence. "
                            "Use only provided memory facts for personal questions.\n"
                            f"User: Speaker: {speaker_name}; "
                            f"Known facts: {('; '.join(known_facts[:2]) if known_facts else 'none')}; "
                            f"Question: {user}\n"
                            "Assistant:"
                        )
                        retry_reply = llama.generate(retry_prompt, max_tokens=min(80, max_tokens), timeout=12)
                    cleaned_reply = _clean_chat_reply(retry_reply) or "[empty response]"

                if _is_low_information_reply(cleaned_reply):
                    cleaned_reply = _grounded_fallback_reply(user, speaker_name, known_facts)

                # Prefer consistent, speaker-grounded output for memory intents.
                if _is_memory_question(user) and _is_unhelpful_memory_reply(cleaned_reply):
                    cleaned_reply = _memory_question_response(user, speaker_name, known_facts)
                print("assistant>", cleaned_reply)
                memory_store.append_turn(speaker_id, user, cleaned_reply)
            except Exception as exc:
                logger.exception("chat_generation_failed")
                print(f"assistant> [error] {exc}")
    except KeyboardInterrupt:
        print("exiting")
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

        env_mode = os.getenv("MODEL_MODE", "mock")
        env_model_path = os.getenv("MODEL_PATH", "")
        env_lib_path = os.getenv("LLAMA_LIB_PATH", "")
        env_memory_db_path = os.getenv("MEMORY_DB_PATH", "data/conversations.sqlite")

        cli_mode = env_mode
        cli_model_path = env_model_path
        cli_lib_path = env_lib_path
        cli_history_turns = 4
        cli_retrieval_turns = 3
        cli_benchmark_memory_retrieval = False
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
            if token == "--retrieval-turns" and idx + 1 < len(sys.argv):
                try:
                    cli_retrieval_turns = max(0, int(sys.argv[idx + 1]))
                except ValueError:
                    print("Invalid --retrieval-turns value; defaulting to 3")
                    cli_retrieval_turns = 3
            if token == "--memory-db-path" and idx + 1 < len(sys.argv):
                cli_memory_db_path = sys.argv[idx + 1]
        if "--benchmark-memory-retrieval" in sys.argv:
            cli_benchmark_memory_retrieval = True

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
