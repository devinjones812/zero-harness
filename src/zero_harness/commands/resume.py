import json
from pathlib import Path

import questionary

from zero_harness import sessions
from zero_harness.commands import self_improve
from zero_harness.tools.registry import summary
from zero_harness.ui import notes
from zero_harness.ui.notes import note

DESCRIPTION = "Pick a saved session and continue it."


async def run(history: list, args: str) -> None:
    """/resume opens a picker; /resume <session file> loads that file."""
    if args:
        path = Path(args)
    else:
        paths = [path for path in sessions.all_sessions() if path != sessions.current]
        if not paths:
            note("no saved sessions")
            return
        choices = [questionary.Choice(sessions.label(path), value=path) for path in paths]
        path = await questionary.select("session:", choices=choices).ask_async()
    if path:
        history[:] = sessions.load(path)
        replay(history)
        note(f"resumed: {sessions.title}")


def replay(history: list) -> None:
    """Print a loaded conversation the way it looked live: messages, tool lines, answers, and self-improve lines."""
    runs = {}
    for run in sessions.improved:
        runs.setdefault(min(run["at"], len(history)), []).append(run["checkpoint"])
    for index, item in enumerate(history):
        for checkpoint in runs.get(index, []):
            self_improve.marker(checkpoint)
        if item.get("role") == "user":
            text = user_text(item["content"])
            if text.startswith(("[background]", "(I undid")):
                note(text.splitlines()[0])
            elif text.startswith("Summary of the conversation so far"):
                note("[summary] earlier messages were summarized")
            else:
                notes.user(text)
        elif item.get("type") == "function_call":
            notes.tool(item["name"], summary(json.loads(item["arguments"])))
        elif item.get("type") == "message" and item.get("role") == "assistant":
            text = "".join(part.get("text", "") for part in item["content"])
            if text.strip():
                notes.section()
                notes.answer(text)
    for checkpoint in runs.get(len(history), []):
        self_improve.marker(checkpoint)


def user_text(content) -> str:
    """A user message's text, with [image] for each attached image."""
    if isinstance(content, str):
        return content
    return " ".join(part["text"] if part["type"] == "input_text" else "[image]" for part in content)
