import inspect

from zero_harness.commands import (
    auto,
    effort,
    model,
    new,
    reload,
    resume,
    self_improve,
    summarize,
    title,
    undo,
)
from zero_harness.ui import notes
from zero_harness.ui.notes import note

COMMANDS = {
    "new": new,
    "resume": resume,
    "model": model,
    "effort": effort,
    "auto": auto,
    "undo": undo,
    "summarize": summarize,
    "title": title,
    "self-improve": self_improve,
    "reload": reload,
}


async def run(text: str, history: list) -> None:
    """Run a /command. Commands change history in place. Unknown commands print the command list."""
    name, _, args = text[1:].partition(" ")
    command = COMMANDS.get(name)
    if command is None:
        note("commands:")
        notes.columns([(f"/{name}", command.DESCRIPTION) for name, command in COMMANDS.items()])
        return
    result = command.run(history, args.strip())
    if inspect.isawaitable(result):
        await result
