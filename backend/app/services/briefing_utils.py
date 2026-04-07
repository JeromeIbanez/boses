from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.briefing import Briefing


def combine_briefing_texts(briefings: list["Briefing"]) -> str:
    """
    Combine extracted_text from multiple briefing objects into a single string
    for injection into simulation prompts.

    - Single briefing with text: returns the text as-is (no change to existing behavior).
    - Multiple briefings: each section is labeled with its title and file type so
      the LLM understands what kind of material the persona is reacting to.
    - Briefings with no extracted_text are skipped.
    """
    parts = []
    non_empty = [b for b in briefings if (b.summary_text or b.extracted_text or "").strip()]

    for i, b in enumerate(non_empty, 1):
        # Prefer AI summary for long briefings; fall back to full extracted text
        raw = (b.summary_text or b.extracted_text or "").strip()
        text = raw
        if len(non_empty) == 1:
            parts.append(text)
        else:
            parts.append(f"BRIEFING {i} ({b.title} · {b.file_type}):\n{text}")

    return "\n\n".join(parts)
