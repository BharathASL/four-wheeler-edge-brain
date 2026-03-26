"""Chat behavior helpers for the interactive chat loop."""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Sequence, Tuple

from src.input_sanitizer import sanitize_for_model_prompt
from src.model_rate_limiter import ModelRateLimiter


ChatTurn = Dict[str, str]
MODEL_COOLDOWN_REPLY = "Please wait a moment before asking another model-heavy question."

_SKIP_REPLY_PREFIXES = (
    "speaker:",
    "known facts:",
    "question:",
    "questio:",
    "grounded sentence:",
    "short grounded sentence:",
    "short sentence:",
    "memory user:",
    "memory assistant:",
    "current user message:",
    "recent conversation:",
    "system:",
)
_REPLY_TOKENS = ("<|assistant|>", "<|user|>", "<|system|>", "<|im_start|>", "<|im_end|>", "[INST]", "[/INST]")
_PROMPT_LEAK_MARKERS = (
    "speaker:",
    "known facts:",
    "question:",
    "memory user:",
    "memory assistant:",
    "current user message:",
    "recent conversation:",
    "system:",
    "<|assistant|>",
    "<|user|>",
    "<|system|>",
    "[inst]",
    "[/inst]",
)
_PERSONAL_FACT_PATTERNS = (
    r"\bmy favorite\s+[a-z]+\s+is\s+",
    r"\bi had\s+.+?\s+for\s+(breakfast|lunch|dinner)\b",
    r"\bi live in\s+",
    r"\bmy name is\s+",
    r"\bi prefer\s+",
    r"\bcall me\s+",
    r"\brefer to me as\s+",
)


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _canonical_fact_key(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    patterns = (
        (r"\bmy favorite\s+([a-z]+)\s+is\b", "favorite:{}"),
        (r"\bi had\s+.+?\s+for\s+(breakfast|lunch|dinner)\b", "meal:{}"),
        (r"\b(call me|refer to me as|from now on call me)\b", "alias"),
        (r"\bi live in\s+([a-z0-9\- ]+)\b", "location"),
        (r"\bmy name is\s+([a-z0-9\- ]+)\b", "name"),
        (r"\bi prefer\s+([a-z0-9\- ]+)\b", "preference:{}"),
    )
    for pattern, key_template in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        if "{}" in key_template and match.lastindex:
            return key_template.format(match.group(match.lastindex).strip())
        return key_template

    return trim_snippet(normalized, max_chars=60)


def _strip_memory_instruction(text: str) -> str:
    stripped = str(text or "").strip()
    stripped = re.sub(r"[\s,.!?:;-]*remember\s+(this|that)\b[\s,.!?:;-]*$", "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def _ensure_sentence(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    if cleaned.endswith((".", "!", "?")):
        return cleaned
    return cleaned + "."


def format_memory_fact_for_reply(fact: str) -> str:
    candidate = _strip_memory_instruction(fact)
    lowered = candidate.lower()
    patterns = (
        (r"^my favorite\s+([a-z]+)\s+is\s+(.+)$", lambda m: f"your favorite {m.group(1)} is {m.group(2).strip()}"),
        (r"^i had\s+(.+?)\s+for\s+(breakfast|lunch|dinner)$", lambda m: f"you had {m.group(1).strip()} for {m.group(2)}"),
        (r"^i live in\s+(.+)$", lambda m: f"you live in {m.group(1).strip()}"),
        (r"^my name is\s+(.+)$", lambda m: f"your name is {m.group(1).strip()}"),
        (r"^i prefer\s+(.+)$", lambda m: f"you prefer {m.group(1).strip()}"),
        (r"^(call me|refer to me as|from now on call me)\s+(.+)$", lambda m: f"you asked me to call you {m.group(2).strip()}"),
    )
    for pattern, formatter in patterns:
        match = re.match(pattern, lowered)
        if match:
            return _ensure_sentence(formatter(match))
    return _ensure_sentence(candidate)


def normalize_personal_fact_for_storage(user_text: str) -> str:
    candidate = str(user_text or "").strip()
    if not candidate or not is_personal_fact_statement(candidate):
        return candidate
    cleaned = _strip_memory_instruction(candidate)
    return _ensure_sentence(cleaned)


def identify_speaker(store, input_func: Callable[[str], str] = input, output_func: Callable[..., None] = print):
    while True:
        speaker_name = input_func("speaker> Who is speaking? ").strip()
        if not speaker_name:
            output_func("Please enter a non-empty speaker name")
            continue
        speaker_id, is_new = store.get_or_create_user(speaker_name)
        if is_new:
            output_func(f"New speaker profile created for: {speaker_name}")
        else:
            output_func(f"Welcome back: {speaker_name}")
        return speaker_id, speaker_name


def clean_chat_reply(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    for token in _REPLY_TOKENS:
        cleaned = cleaned.replace(token, " ")

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    filtered_lines = []

    for line in lines:
        lowered_line = line.lower()
        if lowered_line.startswith(_SKIP_REPLY_PREFIXES):
            continue
        if lowered_line.startswith("answer:"):
            filtered_lines.append(line.split(":", 1)[1].strip())
            continue
        if lowered_line in {"assistant", "assistant:", "answer", "answer:"}:
            continue
        filtered_lines.append(line)

    cleaned = "\n".join(filtered_lines).strip()
    lower = cleaned.lower()
    for prefix in ("assistant:", "assistant", "answer:", "answer"):
        if lower.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" :-\n\t")
            lower = cleaned.lower()

    for prefix in ("current robot assistant response:", "robot assistant response:"):
        if lower.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" :-\n\t")
            lower = cleaned.lower()

    for marker in (
        "\nUser:",
        "\nuser:",
        "User:",
        "user:",
        "\nQuestion:",
        "\nquestion:",
        "\nSystem:",
        "\nsystem:",
    ):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.strip()


def has_prompt_leak(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return any(marker in normalized for marker in _PROMPT_LEAK_MARKERS)


def looks_like_user_perspective_reply(user_text: str, reply_text: str) -> bool:
    intent = detect_chat_intent(user_text)
    normalized = _normalize_text(reply_text)
    normalized_user_text = _normalize_text(user_text)
    if not normalized:
        return False

    safe_prefixes = (
        "i remember",
        "i think",
        "i do not",
        "i don't",
        "i am not sure",
        "from what i remember",
        "you said",
        "you asked me",
        "your name is",
        "you are ",
        "please ",
    )
    if normalized.startswith(safe_prefixes):
        return False

    personal_fact_prefixes = (
        "i had ",
        "my favorite ",
        "i prefer ",
        "i like ",
        "i love ",
        "i live ",
        "call me ",
        "my name is ",
    )
    if normalized.startswith(personal_fact_prefixes) and (
        is_question(user_text) or " my " in f" {normalized_user_text} " or intent.startswith("memory") or intent == "identity_profile"
    ):
        return True

    if intent == "identity_name":
        return normalized.startswith(("my name is ", "i am ", "i'm "))
    if intent == "preference_alias_query":
        return normalized.startswith(("call me ", "refer to me as "))
    if intent in {"identity_profile", "memory_meal", "memory_generic"}:
        return normalized.startswith(personal_fact_prefixes)
    return False


def sanitize_user_facing_reply(user_text: str, reply_text: str, fallback: str = "") -> str:
    cleaned = clean_chat_reply(reply_text)
    if not cleaned:
        return fallback
    if has_prompt_leak(cleaned):
        return fallback
    if looks_like_user_perspective_reply(user_text, cleaned):
        return fallback
    return cleaned


def is_question(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    if lowered.endswith("?"):
        return True
    return lowered.startswith(("what", "why", "how", "when", "where", "who", "do", "did", "are", "can"))


def trim_snippet(text: str, max_chars: int = 140) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."


def _token_set(text: str):
    cleaned = []
    for ch in (text or "").lower():
        cleaned.append(ch if ch.isalnum() or ch.isspace() else " ")
    words = [word for word in "".join(cleaned).split() if len(word) >= 3]
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
    return {word for word in words if word not in stop}


def _fact_score(query: str, fact: str, position: int) -> Tuple[int, int, int]:
    query_tokens = _token_set(query)
    fact_tokens = _token_set(fact)
    overlap = len(query_tokens.intersection(fact_tokens))
    lowered_query = (query or "").lower()
    lowered_fact = (fact or "").lower()
    direct_match = int(any(token in lowered_fact for token in query_tokens))
    phrase_bonus = int("favorite" in lowered_query and "favorite" in lowered_fact)
    phrase_bonus += int("call me" in lowered_query and "call me" in lowered_fact)
    phrase_bonus += int("had for" in lowered_query and "for" in lowered_fact)
    recency_bonus = max(0, 100 - position)
    return overlap, direct_match + phrase_bonus, recency_bonus


def rank_facts_for_query(query: str, facts: Sequence[str]) -> List[str]:
    ranked = sorted(
        enumerate(facts),
        key=lambda item: _fact_score(query, item[1], item[0]),
        reverse=True,
    )
    return [item[1] for item in ranked]


def extract_known_facts(recent_turns: Sequence[ChatTurn], relevant_turns: Sequence[ChatTurn], limit: int = 4) -> List[str]:
    seen = set()
    facts = []
    ordered_turns = list(reversed(list(recent_turns))) + list(relevant_turns)
    for turn in ordered_turns:
        candidate = str(turn.get("user", "")).strip()
        if not candidate or candidate.endswith("?"):
            continue
        key = _canonical_fact_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        facts.append(trim_snippet(candidate, max_chars=100))
        if len(facts) >= limit:
            break
    return facts


def detect_chat_intent(user_text: str) -> str:
    text = (user_text or "").strip().lower()
    if not text:
        return "empty"
    if any(phrase in text for phrase in ("call me ", "refer to me as ", "from now on call me ")):
        return "preference_alias_set"
    if any(
        phrase in text for phrase in ("what did i ask you to call me", "what should you call me", "what do you call me")
    ):
        return "preference_alias_query"
    if any(phrase in text for phrase in ("my name", "who am i", "who i am", "tell my name")):
        return "identity_name"
    if any(
        phrase in text
        for phrase in (
            "what do you know about me",
            "know about me",
            "met before",
            "have we met",
            "remember me",
            "remeber me",
        )
    ):
        return "identity_profile"
    if any(meal in text for meal in ("dinner", "lunch", "breakfast")) and any(
        marker in text for marker in ("had for", "for the", "for dinner", "for lunch", "for breakfast")
    ):
        return "memory_meal"
    if any(
        phrase in text
        for phrase in (
            "what is my favorite",
            "what's my favorite",
            "what is my preferred",
            "what's my preferred",
            "what color do i like",
            "what do i like",
        )
    ):
        return "memory_generic"
    if any(phrase in text for phrase in ("remember", "remeber", "what did i", "know about me", "had for")):
        return "memory_generic"
    if is_question(text):
        return "question"
    return "statement"


def is_personal_fact_statement(user_text: str) -> bool:
    text = _normalize_text(user_text)
    if not text or is_question(text):
        return False
    if "remember this" in text or "remember that" in text:
        return True
    return any(re.search(pattern, text) for pattern in _PERSONAL_FACT_PATTERNS)


def deterministic_personal_response(user_text: str, speaker: str, facts: Sequence[str]) -> str:
    intent = detect_chat_intent(user_text)
    if intent == "identity_name":
        return f"Your name is {speaker}."
    if intent == "preference_alias_query":
        alias = extract_alias_preference(facts)
        if alias:
            return f"You asked me to call you {alias}."
        return f"I remember you as {speaker}, but I do not have a saved preferred name yet."
    if intent == "identity_profile":
        if not facts:
            return f"You are {speaker}. I do not have additional verified facts yet."
        summarized = "; ".join(format_memory_fact_for_reply(fact).rstrip(".") for fact in facts[:3])
        return f"You are {speaker}. From our prior conversation: {summarized}."
    return ""


def extract_meal_fact(turn_texts: Sequence[str], meal_name: str) -> str:
    patterns = (
        rf"\bi\s+had\s+(.+?)\s+for\s+{meal_name}\b",
        rf"\bhad\s+(.+?)\s+for\s+{meal_name}\b",
        rf"\bfor\s+{meal_name}\s+i\s+had\s+(.+?)\b",
    )

    for text in reversed(list(turn_texts)):
        candidate = " ".join(str(text or "").strip().split())
        if not candidate:
            continue
        lowered = candidate.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue
            meal_value = match.group(1).strip(" .,!?:;-")
            if meal_value:
                return meal_value
    return ""


def deterministic_meal_memory_response(
    user_text: str,
    speaker: str,
    recent_turns: Sequence[ChatTurn],
    relevant_turns: Sequence[ChatTurn],
) -> str:
    if detect_chat_intent(user_text) != "memory_meal":
        return ""

    lowered = (user_text or "").lower()
    asked_meal = ""
    for meal in ("dinner", "lunch", "breakfast"):
        if meal in lowered:
            asked_meal = meal
            break
    if not asked_meal:
        return ""

    turn_texts = [turn.get("user", "") for turn in list(recent_turns) + list(relevant_turns)]
    meal_fact = extract_meal_fact(turn_texts, asked_meal)
    if meal_fact:
        return f"You said you had {meal_fact} for {asked_meal}."

    return (
        f"I remember you as {speaker}, but I do not have your {asked_meal} detail saved yet. "
        "Tell me once and I will remember it for next time."
    )


def is_memory_question(user_text: str) -> bool:
    return detect_chat_intent(user_text) in {
        "identity_profile",
        "memory_meal",
        "memory_generic",
        "preference_alias_query",
    }


def extract_alias_preference(facts: Sequence[str]) -> str:
    patterns = (
        r"\bcall me\s+(.+?)(?:\s+from now on)?[\.!]?$",
        r"\brefer to me as\s+(.+?)[\.!]?$",
        r"\bfrom now on call me\s+(.+?)[\.!]?$",
    )
    for fact in reversed(list(facts)):
        lowered = str(fact or "").strip().lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                alias = match.group(1).strip(" \"'.,!?:;-")
                if alias:
                    return alias
    return ""


def memory_confidence(user_text: str, facts: Sequence[str], top_fact: str | None = None) -> str:
    if not facts:
        return "low"
    query_tokens = _token_set(user_text)
    if not query_tokens:
        return "medium"

    # If top_fact is provided (already selected by the caller), use it directly to
    # avoid re-ranking and ensure confidence wording matches the returned fact.
    if top_fact is None:
        ranked_facts = rank_facts_for_query(user_text, facts)
        top_fact = ranked_facts[0]

    top_tokens = _token_set(top_fact)
    best_overlap = len(query_tokens.intersection(top_tokens))
    if best_overlap >= 2:
        return "high"
    if best_overlap == 1:
        return "medium"
    return "low"


def memory_question_response(user_text: str, speaker: str, facts: Sequence[str]) -> str:
    if detect_chat_intent(user_text) == "preference_alias_query":
        alias = extract_alias_preference(facts)
        if alias:
            return f"You asked me to call you {alias}."
        return f"I remember you as {speaker}, but I do not have a saved preferred name yet."

    if not facts:
        return (
            f"I remember you as {speaker}, but I do not have that detail saved yet. "
            "Tell me once and I will remember it for next time."
        )

    ranked_facts = rank_facts_for_query(user_text, facts)
    top_fact = ranked_facts[0]
    formatted_fact = format_memory_fact_for_reply(top_fact)
    confidence = memory_confidence(user_text, facts, top_fact=top_fact)
    if confidence == "high":
        return f"From what I remember: {formatted_fact}"
    if confidence == "medium":
        return f"I think this is what you mentioned: {formatted_fact}"
    return (
        f"I remember you as {speaker}, but I am not confident about that detail yet. "
        "If you share it once, I will store it and recall it later."
    )


def is_low_information_reply(text: str) -> bool:
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return True
    if has_prompt_leak(normalized):
        return True
    if "empty response" in normalized:
        return True
    if normalized.startswith(("assist", "assistant", "<|assistant|>")):
        return True
    if normalized in {"memory", "ok", "okay", "noted", "i see", "yes", "no"}:
        return True
    if len(normalized.split()) <= 2 and len(normalized) <= 14:
        return True
    return False


def is_unhelpful_memory_reply(text: str) -> bool:
    normalized = " ".join((text or "").strip().lower().split())
    if not normalized:
        return True
    patterns = (
        "current robot assistant response",
        "i do not have any memories",
        "i don't have any memories",
        "i have no memories",
        "no memories",
        "i do not have personal memories",
        "i don't have personal memories",
        "i do not remember",
        "i don't remember",
    )
    return any(pattern in normalized for pattern in patterns)


def grounded_fallback_reply(user_text: str, speaker: str, facts: Sequence[str]) -> str:
    if is_personal_fact_statement(user_text):
        return f"Got it, {speaker}. I have noted: {trim_snippet(user_text, max_chars=120)}"
    if is_memory_question(user_text):
        return memory_question_response(user_text, speaker, facts)
    ranked_facts = rank_facts_for_query(user_text, facts)
    if is_question(user_text):
        if ranked_facts:
            return f"From what I remember: {format_memory_fact_for_reply(ranked_facts[0])}"
        return f"I remember you as {speaker}, but I need a bit more detail to answer reliably."
    return f"Got it, {speaker}. I have noted: {trim_snippet(user_text, max_chars=120)}"


def effective_retrieval_limit(user_text: str, retrieval_turns: int) -> int:
    if is_memory_question(user_text):
        return max(retrieval_turns, 3)
    return retrieval_turns


def dedupe_relevant_turns(recent_turns: Sequence[ChatTurn], relevant_turns: Sequence[ChatTurn]) -> List[ChatTurn]:
    recent_pairs = {(turn["user"], turn["assistant"]) for turn in recent_turns}
    return [turn for turn in relevant_turns if (turn["user"], turn["assistant"]) not in recent_pairs]


def build_chat_messages(
    user_text: str,
    speaker_name: str,
    recent_turns: Sequence[ChatTurn],
    relevant_turns: Sequence[ChatTurn],
) -> List[Dict[str, str]]:
    relevant_cap = 3 if is_memory_question(user_text) else 2
    curated_recent_turns = list(recent_turns)[-4:]
    curated_relevant_turns = list(relevant_turns)[:relevant_cap]

    system_lines = [
        "You are an offline robot assistant.",
        "Reply briefly and clearly.",
        "Use only the provided speaker profile and memory snippets for personal facts.",
        "If a personal fact is unknown in memory, explicitly say you do not know.",
        "Do not invent biography details.",
        "Do not repeat prompt labels such as Speaker, Known facts, User, Assistant, or Memory.",
        "For personal-memory answers, speak to the user directly instead of answering as if you are the user.",
        f"Current speaker name: {speaker_name}",
    ]

    user_lines = []
    if curated_relevant_turns:
        user_lines.append("Relevant older memory snippets:")
        for turn in curated_relevant_turns:
            user_lines.append(f"Memory User: {sanitize_for_model_prompt(trim_snippet(turn['user']))}")
            user_lines.append(f"Memory Assistant: {sanitize_for_model_prompt(trim_snippet(turn['assistant']))}")

    user_lines.append("Recent conversation:")
    for turn in curated_recent_turns:
        user_lines.append(f"User: {sanitize_for_model_prompt(trim_snippet(turn['user']))}")
        user_lines.append(f"Assistant: {sanitize_for_model_prompt(trim_snippet(turn['assistant']))}")
    user_lines.append(f"Current user message: {sanitize_for_model_prompt(user_text)}")

    return [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


def _retry_messages(user_text: str, speaker_name: str, known_facts: Sequence[str], intent: str) -> List[Dict[str, str]]:
    intent_hint = {
        "identity_name": "Answer the speaker identity question directly.",
        "identity_profile": "Answer only from known speaker facts.",
        "memory_meal": "Answer only with the stored meal detail if present.",
        "memory_generic": "Answer only from remembered facts and say when uncertain.",
    }.get(intent, "Answer in one short grounded sentence.")

    return [
        {
            "role": "system",
            "content": (
                "You are an offline robot assistant. "
                "Answer in one short sentence. "
                "Use only provided memory facts for personal questions. "
                + intent_hint
            ),
        },
        {
            "role": "user",
            "content": (
                f"Speaker: {speaker_name}\n"
                f"Known facts: {sanitize_for_model_prompt('; '.join(known_facts[:2]) if known_facts else 'none')}\n"
                f"Question: {sanitize_for_model_prompt(user_text)}"
            ),
        },
    ]


def _generate_with_adapter(llama, messages: Sequence[Dict[str, str]], max_tokens: int, timeout: int) -> str:
    if hasattr(llama, "generate_chat"):
        return llama.generate_chat(list(messages), max_tokens=max_tokens, timeout=timeout)

    prompt = (
        "System:\n"
        + str(messages[0]["content"])
        + "\n\nUser:\n"
        + str(messages[1]["content"])
        + "\nAssistant:"
    )
    return llama.generate(prompt, max_tokens=max_tokens, timeout=timeout)


def generate_chat_reply(
    llama,
    user_text: str,
    speaker_name: str,
    recent_turns: Sequence[ChatTurn],
    relevant_turns: Sequence[ChatTurn],
    max_tokens: int = 128,
    model_rate_limiter: ModelRateLimiter | None = None,
) -> str:
    known_facts = extract_known_facts(recent_turns, relevant_turns)

    deterministic_meal = deterministic_meal_memory_response(
        user_text,
        speaker_name,
        recent_turns,
        relevant_turns,
    )
    if deterministic_meal:
        return deterministic_meal

    deterministic_personal = deterministic_personal_response(user_text, speaker_name, known_facts)
    if deterministic_personal:
        return deterministic_personal

    if is_personal_fact_statement(user_text):
        return grounded_fallback_reply(user_text, speaker_name, known_facts)

    if model_rate_limiter is not None:
        allowed, _retry_after = model_rate_limiter.allow()
        if not allowed:
            return MODEL_COOLDOWN_REPLY

    messages = build_chat_messages(user_text, speaker_name, recent_turns, relevant_turns)
    reply = _generate_with_adapter(llama, messages, max_tokens=max_tokens, timeout=20)
    cleaned_reply = sanitize_user_facing_reply(user_text, reply) or "[empty response]"

    if is_low_information_reply(cleaned_reply):
        retry_messages = _retry_messages(
            user_text,
            speaker_name,
            known_facts,
            detect_chat_intent(user_text),
        )
        retry_reply = _generate_with_adapter(llama, retry_messages, max_tokens=min(80, max_tokens), timeout=12)
        cleaned_reply = sanitize_user_facing_reply(user_text, retry_reply) or "[empty response]"

    if is_low_information_reply(cleaned_reply):
        cleaned_reply = grounded_fallback_reply(user_text, speaker_name, known_facts)

    if is_memory_question(user_text) and is_unhelpful_memory_reply(cleaned_reply):
        cleaned_reply = memory_question_response(user_text, speaker_name, known_facts)

    return cleaned_reply


__all__ = [
    "clean_chat_reply",
    "dedupe_relevant_turns",
    "detect_chat_intent",
    "effective_retrieval_limit",
    "extract_alias_preference",
    "extract_known_facts",
    "format_memory_fact_for_reply",
    "generate_chat_reply",
    "grounded_fallback_reply",
    "identify_speaker",
    "is_low_information_reply",
    "is_memory_question",
    "memory_confidence",
    "memory_question_response",
    "MODEL_COOLDOWN_REPLY",
    "normalize_personal_fact_for_storage",
    "rank_facts_for_query",
    "sanitize_user_facing_reply",
]