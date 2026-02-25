from __future__ import annotations

import re

MEMORY_LINE_PATTERN = re.compile(r"^\d+\.\s\[[^\]]+\]\s\([^)]*\)\s*")
SUMMARY_LINE_PATTERN = re.compile(r"^\d+\.\s\[[^\]]+\]\s*")


def _first_context_hint(prompt_context: str) -> str | None:
    in_memory = False
    in_summary = False

    for raw_line in prompt_context.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "Retrieved memory:":
            in_memory = True
            in_summary = False
            continue
        if line == "Recent summaries:":
            in_memory = False
            in_summary = True
            continue
        if line == "Recent timeline events:":
            in_memory = False
            in_summary = False
            continue

        if in_memory and line != "none":
            hint = MEMORY_LINE_PATTERN.sub("", line).strip()
            if hint:
                return hint[:220]
        if in_summary and line != "none":
            hint = SUMMARY_LINE_PATTERN.sub("", line).strip()
            if hint:
                return hint[:220]

    return None


def compose_gm_response(
    *,
    provider: str,
    model: str | None,
    language: str,
    player_input: str,
    prompt_context: str,
) -> str:
    provider_label = provider.strip().lower() or "codex"
    model_label = model.strip() if model else "auto"
    normalized_input = player_input.strip()
    hint = _first_context_hint(prompt_context)
    context_line = hint or "The situation remains uncertain and tense."

    if language == "fr":
        return (
            f"[{provider_label}:{model_label}] "
            f"L'univers reagit a votre action: {normalized_input}\n"
            f"Consequence immediate: {context_line}\n"
            "Choix proposes: 1) Avancer, 2) Observer, 3) Se replier."
        )

    return (
        f"[{provider_label}:{model_label}] "
        f"The world reacts to your action: {normalized_input}\n"
        f"Immediate consequence: {context_line}\n"
        "Choices: 1) Push forward, 2) Investigate, 3) Regroup."
    )
