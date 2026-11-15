
"""Conversation memory strategies for ShopAssist Pro.

The server manages conversation history and decides how much
history to send to the LLM on each call.

Supported strategies:
- window: Keep only the most recent N conversation turns.
- summary: Summarise older turns and retain recent turns.
"""

import os

from langchain_core.messages import HumanMessage, SystemMessage


STRATEGY = (os.getenv("MEMORY") or "window").strip().lower()
KEEP_TURNS = int(os.getenv("KEEP_TURNS") or 4)

if STRATEGY not in ("window", "summary"):
    raise ValueError(
        f"Invalid MEMORY strategy '{STRATEGY}'. "
        "Allowed values are: window, summary"
    )

if KEEP_TURNS < 3:
    raise ValueError("KEEP_TURNS must be at least 3.")


def window(history: list, keep_turns: int = KEEP_TURNS) -> list:
    """Keep only the most recent N conversation turns.

    One turn = one human message + one AI message.
    """

    if keep_turns < 3:
        raise ValueError("KEEP_TURNS must be at least 3.")

    recent_messages = keep_turns * 2

    return history[-recent_messages:]

SUMMARY_PROMPT = (
    "Summarise this store conversation in at most 5 short bullet points. "
    "Keep every name, order number, pincode and figure the CUSTOMER gave. "
    "Do not add anything that was not said."
)


def summarise(
    history: list,
    llm,
    keep_turns: int = KEEP_TURNS
) -> list:
    """Summarise older messages and preserve recent messages."""

    if keep_turns < 3:
        raise ValueError("KEEP_TURNS must be at least 3.")

    recent_count = 2 * keep_turns

    if len(history) <= recent_count:
        return history

    old = history[:-recent_count]
    recent = history[-recent_count:]

    transcript = "\n".join(
        f"{type(message).__name__}: {message.content}"
        for message in old
    )

    summary = llm.invoke([
        SystemMessage(content=SUMMARY_PROMPT),
        HumanMessage(content=transcript)
    ]).content

    return [
        SystemMessage(
            content=f"Summary of the earlier conversation:\n{summary}"
        )
    ] + recent


def trim(history: list, llm=None) -> list:
    """Select the configured memory strategy."""

    if STRATEGY == "window":
        return window(history, KEEP_TURNS)

    if STRATEGY == "summary":
        if llm is None:
            raise ValueError(
                "An LLM instance is required for summary memory."
            )

        return summarise(history, llm, KEEP_TURNS)

    raise ValueError(f"Unsupported memory strategy: {STRATEGY}")
