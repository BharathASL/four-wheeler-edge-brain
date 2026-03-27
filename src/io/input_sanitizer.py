"""Sanitize user-provided text before inserting it into model prompts."""

from __future__ import annotations

import re


ROLE_PREFIXES = (
    "system:",
    "assistant:",
    "user:",
    "developer:",
    "instruction:",
    "question:",
    "answer:",
)

SPECIAL_TOKENS = (
    "<|system|>",
    "<|assistant|>",
    "<|user|>",
    "<|end|>",
)


def sanitize_for_model_prompt(text: str) -> str:
    cleaned = str(text or "")
    for token in SPECIAL_TOKENS:
        cleaned = cleaned.replace(token, f"[{token.strip('<|>')}]")

    lines = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith(ROLE_PREFIXES):
            prefix, remainder = line.split(":", 1)
            line = f"quoted {prefix.strip().lower()} - {remainder.strip()}"
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = cleaned.replace("```", "'''")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


__all__ = ["sanitize_for_model_prompt"]