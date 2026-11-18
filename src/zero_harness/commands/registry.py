import inspect

from zero_harness.commands import auto, model, resume, summarize, title, undo
from zero_harness.ui.notes import note

COMMANDS = {"summarize": summarize, "model": model, "resume": resume, "title": title, "auto": auto, "undo": undo}


async def run(text: str, history: list) -> None:
    """Run a /command. Commands change history in place. Unknown commands print the command list."""
    name, _, args = text[1:].partition(" ")
    command = COMMANDS.get(name)
    if command is None:
        note("commands:")
        for name, command in COMMANDS.items():
            note(f"  /{name}  {command.DESCRIPTION}")
        return
    result = command.run(history, args.strip())
    if inspect.isawaitable(result):
        await result
