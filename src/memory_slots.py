"""Structured personal-memory slots for deterministic extraction and recall."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence


@dataclass(frozen=True)
class MemorySlot:
    name: str
    value: str
    updated_at: float | None = None


SUPPORTED_SLOT_NAMES = (
    "name",
    "preferred_name",
    "pet_name",
    "city",
    "favorite_color",
    "favorite_food",
    "programming_language",
    "project_summary",
    "remembered_number",
)

_SESSION_DIRECTIVE_PATTERNS = (
    r"\balways respond\b",
    r"\brespond\s+(concisely|briefly|in one sentence|with one sentence)\b",
    r"\bkeep (your )?repl(?:y|ies)\s+(short|brief|concise)\b",
    r"\banswer\s+(concisely|briefly|in one sentence|with one sentence)\b",
    r"\bone sentence\b",
)
_CORRECTION_MARKERS = ("actually", "change it to", "change that to", "it's now", "it is now", "now prefer")
_UNSAFE_MEMORY_LABEL_PATTERN = re.compile(r"\b(?:user|speaker)\s*\d+\s*:", flags=re.IGNORECASE)


def _normalize_whitespace(text: str) -> str:
    return " ".join((text or "").strip().split())


def _normalize_slot_value(value: str) -> str:
    cleaned = _normalize_whitespace(value).strip(" \"'.,!?:;-")
    return cleaned


def detect_session_directive(text: str) -> str | None:
    normalized = _normalize_whitespace(text).lower()
    if not normalized:
        return None
    if any(re.search(pattern, normalized) for pattern in _SESSION_DIRECTIVE_PATTERNS):
        return "response_style"
    return None


def detect_unsafe_memory_input(text: str) -> str | None:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return None
    labels = _UNSAFE_MEMORY_LABEL_PATTERN.findall(normalized)
    if len(labels) >= 2:
        return "multi_speaker"
    return None


def _contains_correction_marker(text: str) -> bool:
    normalized = _normalize_whitespace(text).lower()
    return any(marker in normalized for marker in _CORRECTION_MARKERS)


def _latest_slot(existing_slots: Mapping[str, MemorySlot]) -> MemorySlot | None:
    if not existing_slots:
        return None
    return max(existing_slots.values(), key=lambda slot: slot.updated_at or 0.0)


def _build_slot(name: str, value: str, timestamp: float) -> MemorySlot | None:
    cleaned_value = _normalize_slot_value(value)
    if not cleaned_value:
        return None
    return MemorySlot(name=name, value=cleaned_value, updated_at=timestamp)


def _explicit_slot_matches(text: str, timestamp: float) -> List[MemorySlot]:
    slots: List[MemorySlot] = []
    patterns = (
        ("name", r"\bmy name is\s+(.+?)(?=\s+and\s+i(?:\s+am|'m)\b|,|[.!?]|$)"),
        ("preferred_name", r"\b(?:call me|refer to me as|from now on call me)\s+(.+?)(?:\s+from now on)?(?:[.!?]|$)"),
        ("favorite_color", r"\bmy favorite color is\s+(.+?)(?:[.!?]|$)"),
        ("favorite_color", r"\bmy color is\s+(.+?)(?:[.!?]|$)"),
        ("favorite_food", r"\bmy favorite food is\s+(.+?)(?:[.!?]|$)"),
        ("favorite_food", r"\bi like to eat\s+(.+?)(?:[.!?]|$)"),
        ("favorite_food", r"\bi like\s+([A-Za-z][A-Za-z0-9\- ]+?)\s+on\s+weekends?(?:[.!?]|$)"),
        ("favorite_food", r"\bi enjoy eating\s+([A-Za-z][A-Za-z0-9\- ]+?)\s+on\s+weekends?(?:[.!?]|$)"),
        ("city", r"\bi live in\s+(.+?)(?:,|\s+and\s+|[.!?]|$)"),
        ("pet_name", r"\bi have a\s+(?:dog|cat|pet)\s+named\s+(.+?)(?:[,.!?]|$)"),
        ("programming_language", r"\bmy favorite language is\s+(.+?)(?:[.!?]|$)"),
        ("programming_language", r"\bi like\s+([A-Za-z0-9+#\-. ]+?)\s+programming(?:[.!?]|$)"),
        ("programming_language", r"\bi prefer\s+([A-Za-z0-9+#\-. ]+?)(?:\s+over\s+.+?|\s+more than\s+.+?)?(?:\s+and\s+|[.!?]|$)"),
        ("programming_language", r"\bi now prefer\s+([A-Za-z0-9+#\-. ]+?)(?:\s+over\s+.+?|\s+more than\s+.+?)?(?:\s+and\s+|[.!?]|$)"),
        ("remembered_number", r"\bremember\s+(?:this\s+)?number\s*:?\s*(\d+)(?:[.!?]|$)"),
        ("project_summary", r"\bi am building\s+(.+?)(?:\s+remember this(?: for future conversations)?|[.!?]|$)"),
        ("project_summary", r"\bi'?m building\s+(.+?)(?:\s+remember this(?: for future conversations)?|[.!?]|$)"),
    )

    for slot_name, pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            slot = _build_slot(slot_name, match.group(1), timestamp)
            if slot is not None:
                slots.append(slot)
    return slots


def _infer_correction_slot(text: str, existing_slots: Mapping[str, MemorySlot]) -> str | None:
    lowered = _normalize_whitespace(text).lower()
    if "color" in lowered:
        return "favorite_color"
    if "food" in lowered or "eat" in lowered:
        return "favorite_food"
    if "language" in lowered or "programming" in lowered or "prefer" in lowered:
        return "programming_language"
    if "live in" in lowered or "city" in lowered:
        return "city"
    if "dog" in lowered or "cat" in lowered or "pet" in lowered:
        return "pet_name"
    if "call me" in lowered or "refer to me as" in lowered:
        return "preferred_name"
    if "my name" in lowered:
        return "name"
    if "number" in lowered:
        return "remembered_number"
    if "building" in lowered or "project" in lowered:
        return "project_summary"
    if _contains_correction_marker(lowered):
        latest = _latest_slot(existing_slots)
        if latest is not None:
            return latest.name
    return None


def _extract_correction_value(slot_name: str, text: str) -> str:
    patterns = (
        r"\bchange (?:it|that) to\s+(.+?)(?:[.!?]|$)",
        r"\bit'?s now\s+(.+?)(?:[.!?]|$)",
        r"\bit is now\s+(.+?)(?:[.!?]|$)",
        r"\bactually,?\s+my [a-z ]+ is\s+(.+?)(?:[.!?]|$)",
        r"\bactually,?\s+i live in\s+(.+?)(?:[.!?]|$)",
    )

    if slot_name == "programming_language":
        specialized = re.search(
            r"\b(?:i now prefer|i prefer)\s+([A-Za-z0-9+#\-. ]+?)(?:\s+over\s+.+?|\s+more than\s+.+?)?(?:\s+and\s+|[.!?]|$)",
            text,
            flags=re.IGNORECASE,
        )
        if specialized:
            return specialized.group(1)

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def apply_slot_update(text: str, existing_slots: Mapping[str, MemorySlot]) -> List[MemorySlot]:
    timestamp = time.time()
    target_slot = _infer_correction_slot(text, existing_slots)
    if not target_slot:
        return []

    correction_value = _extract_correction_value(target_slot, text)
    slot = _build_slot(target_slot, correction_value, timestamp)
    if slot is None:
        return []
    return [slot]


def extract_slots_from_input(text: str, existing_slots: Mapping[str, MemorySlot] | None = None) -> List[MemorySlot]:
    existing_slots = existing_slots or {}
    if detect_session_directive(text):
        return []
    if detect_unsafe_memory_input(text):
        return []

    timestamp = time.time()
    extracted = _explicit_slot_matches(text, timestamp)
    if not extracted and _contains_correction_marker(text):
        extracted = apply_slot_update(text, existing_slots)

    deduped: dict[str, MemorySlot] = {}
    for slot in extracted:
        deduped[slot.name] = slot
    return [deduped[name] for name in SUPPORTED_SLOT_NAMES if name in deduped]


def extract_requested_slot_names(text: str) -> List[str]:
    lowered = _normalize_whitespace(text).lower()
    requested: List[str] = []
    detectors = (
        ("preferred_name", ("what did i ask you to call me", "what should you call me", "what do you call me")),
        ("name", ("what is my name", "what's my name", "who am i", "my name")),
        ("pet_name", ("dog's name", "dogs name", "pet name", "my pet", "my dog")),
        ("city", ("where do i live", "where i live", "my city", "city")),
        ("favorite_color", ("favorite color", "what color do i like", "color do i like")),
        ("favorite_food", ("favorite food", "what food do i like", "what kind of food do i like", "food do i like")),
        ("programming_language", ("favorite language", "programming language", "what language do i prefer", "what do i like programming", "language do i like")),
        ("project_summary", ("what am i building", "what i'm building", "what i am building", "what project")),
        ("remembered_number", ("what number did i ask you to remember", "remembered number", "what number")),
    )
    for slot_name, phrases in detectors:
        if any(phrase in lowered for phrase in phrases):
            requested.append(slot_name)
    return requested


def format_memory_slot_for_reply(slot_name: str, value: str) -> str:
    cleaned_value = _normalize_slot_value(value)
    templates = {
        "name": f"your name is {cleaned_value}",
        "preferred_name": f"you asked me to call you {cleaned_value}",
        "pet_name": f"your dog's name is {cleaned_value}",
        "city": f"you live in {cleaned_value}",
        "favorite_color": f"your favorite color is {cleaned_value}",
        "favorite_food": f"you like {cleaned_value}",
        "programming_language": f"you like {cleaned_value} programming",
        "project_summary": f"you are building {cleaned_value}",
        "remembered_number": f"the number you asked me to remember is {cleaned_value}",
    }
    return templates.get(slot_name, cleaned_value)


def describe_missing_slot(slot_name: str) -> str:
    labels = {
        "name": "name",
        "preferred_name": "preferred name",
        "pet_name": "dog's name",
        "city": "city",
        "favorite_color": "favorite color",
        "favorite_food": "favorite food",
        "programming_language": "preferred programming language",
        "project_summary": "project",
        "remembered_number": "remembered number",
    }
    return labels.get(slot_name, slot_name.replace("_", " "))


def join_slot_phrases(phrases: Sequence[str]) -> str:
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"


def format_memory_slot_acknowledgement(slots: Iterable[MemorySlot]) -> str:
    phrases = [format_memory_slot_for_reply(slot.name, slot.value) for slot in slots]
    return join_slot_phrases(phrases)


__all__ = [
    "MemorySlot",
    "SUPPORTED_SLOT_NAMES",
    "apply_slot_update",
    "describe_missing_slot",
    "detect_session_directive",
    "detect_unsafe_memory_input",
    "extract_requested_slot_names",
    "extract_slots_from_input",
    "format_memory_slot_acknowledgement",
    "format_memory_slot_for_reply",
    "join_slot_phrases",
]