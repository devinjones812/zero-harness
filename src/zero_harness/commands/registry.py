import inspect

from zero_harness.commands import (
    mode,
    model,
    new,
    reasoning,
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
    "reasoning": reasoning,
    "mode": mode,
    "undo": undo,
    "summarize": summarize,
    "title": title,
    "self-improve": self_improve,
    "reload": reload,
}


def options() -> dict:
    """Each command's name and a function from the words typed after it to the next word's options, for Tab completion.

    Commands define complete(words), or OPTIONS for a single fixed word.
    """
    return {name: getattr(command, "complete", fixed(command)) for name, command in COMMANDS.items()}


def fixed(command):
    return lambda words: [] if words else getattr(command, "OPTIONS", [])


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
