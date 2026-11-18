import inspect

from zero_harness.commands import (
    effort,
    mode,
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
    "mode": mode,
    "undo": undo,
    "summarize": summarize,
    "title": title,
    "self-improve": self_improve,
    "reload": reload,
}


def options() -> dict[str, list[str]]:
    """Each command's name and the options it takes, for Tab completion."""
    return {name: getattr(command, "OPTIONS", []) for name, command in COMMANDS.items()}


def anytime(text: str) -> bool:
    """True if the /command may run while the agent works."""
    command = COMMANDS.get(text[1:].partition(" ")[0])
    return getattr(command, "ANYTIME", False)


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
