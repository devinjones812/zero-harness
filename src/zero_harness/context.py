"""Keeps `history` small as a session grows. Every call resends all of it,
so large old tool results cost tokens on every call until removed.

Thresholds are set for cost, far below the model's context limit."""

from zero_harness import llm, usage
from zero_harness.ui import notes

TRIM_AT_TOKENS = 100_000
COMPACT_AT_TOKENS = 200_000
KEEP_RESULTS = 5
KEEP_IMAGES = 3

STUB = "(old tool result removed to save context. Run the tool again if you need it.)"
IMAGE_STUB = "(old image removed to save context. Ask the user to attach it again if you need it.)"

SUMMARY_REQUEST = """Summarize this conversation so you can continue it with no other context.
Include:
- The user's latest request before this message, word for word.
- Goals, decisions, and constraints from the user.
- Files read or changed, with the important details.
- What is done, what is left, and the next step.
Plain text only. Do not call tools."""


async def manage(history: list, tools: list) -> None:
    """Trim or compact history based on the last call's input tokens. Call only when every tool call has its output.
    `tools` are the schemas the conversation sends, for compact()."""
    input_tokens = usage.input_tokens
    if input_tokens is None:
        return
    if input_tokens > COMPACT_AT_TOKENS:
        await compact(history, f"last call used {input_tokens:,} input tokens (limit {COMPACT_AT_TOKENS:,})", tools)
    elif input_tokens > TRIM_AT_TOKENS:
        trim(history, f"last call used {input_tokens:,} input tokens (limit {TRIM_AT_TOKENS:,})")


def trim(history: list, why: str) -> None:
    """In place: stub all but the last KEEP_RESULTS tool outputs and KEEP_IMAGES images in user messages."""
    results = [item for item in history if item.get("type") == "function_call_output"]
    old_results = [item for item in results[:-KEEP_RESULTS] if item["output"] != STUB]
    for item in old_results:
        item["output"] = STUB

    images = [
        (item["content"], index)
        for item in history
        if item.get("role") == "user" and isinstance(item["content"], list)
        for index, part in enumerate(item["content"])
        if part["type"] == "input_image"
    ]
    old_images = images[:-KEEP_IMAGES]
    for parts, index in old_images:
        parts[index] = {"type": "input_text", "text": IMAGE_STUB}

    if old_results or old_images:
        notes.note(
            f"[context] trim: {why}. Removed {len(old_results)} old tool results and {len(old_images)} old images, "
            f"kept the last {KEEP_RESULTS} results and {KEEP_IMAGES} images."
        )


async def compact(history: list, why: str, tools: list) -> None:
    """In place: replace history with one message, a model-written summary of it."""
    notes.note("[context] summarizing...")
    summary = await llm.complete(history + [{"role": "user", "content": SUMMARY_REQUEST}], tools)
    notes.note(f"[context] compact: {why}. Replaced {len(history)} history items with a {len(summary):,}-char summary.")
    history[:] = [
        {"role": "user", "content": f"Summary of the conversation so far:\n\n{summary}\n\nContinue from here."}
    ]
