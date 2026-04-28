"""Common helpers for displaying ADK events in notebooks and Streamlit.

The big one is `final_text()` — it skips reasoning parts on reasoning
models like gpt-oss, where the final response carries multiple Parts and
only the non-thought ones are intended for the user.
"""

from __future__ import annotations

from typing import Iterable

from google.adk.events import Event


def visible_parts(event: Event) -> list:
    """Return parts of an event that are meant for the user (not reasoning)."""
    if not event.content or not event.content.parts:
        return []
    return [p for p in event.content.parts if not getattr(p, "thought", False)]


def thought_parts(event: Event) -> list:
    """Return reasoning/thought parts of an event."""
    if not event.content or not event.content.parts:
        return []
    return [p for p in event.content.parts if getattr(p, "thought", False)]


def final_text(event: Event) -> str:
    """Concatenate the user-facing text of a final response event."""
    parts = visible_parts(event)
    return "".join(p.text for p in parts if getattr(p, "text", None))


def collect_final_text(events: Iterable[Event]) -> str:
    """Walk a stream of events and return the concatenated final text."""
    chunks = []
    for ev in events:
        if ev.is_final_response():
            t = final_text(ev)
            if t:
                chunks.append(t)
    return "\n".join(chunks)
