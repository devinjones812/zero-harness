"""Errors a turn survives. recoverable() lists them, report() shows one to the user, and repair() gives every unanswered
tool call an output so the next request is valid."""

import sys

from zero_harness.ui.notes import note


class StreamError(Exception):
    """The response stream ended without a completed response."""


class RateLimited(Exception):
    """The provider still refused after the SDK's retries and zero's wait. The message says which limit."""


def recoverable() -> tuple[type[Exception], ...]:
    """API errors a turn survives. SDKs load on first use, so only loaded ones can have raised."""
    sdks = [sys.modules[name] for name in ("openai", "anthropic") if name in sys.modules]
    return (*(sdk.APIError for sdk in sdks), StreamError, RateLimited)


INTERRUPTED = "interrupted: this tool did not run or did not finish."


def report(error: Exception) -> None:
    note(str(error) if isinstance(error, RateLimited) else f"error: {type(error).__name__}: {error}", style="red")
    note("Conversation kept. Send a message to retry.")


def repair(history: list) -> None:
    """In place: give every unanswered tool call an output. The API rejects a call without one."""
    answered = {item["call_id"] for item in history if item.get("type") == "function_call_output"}
    for item in list(history):
        if item.get("type") == "function_call" and item["call_id"] not in answered:
            history.append({"type": "function_call_output", "call_id": item["call_id"], "output": INTERRUPTED})
