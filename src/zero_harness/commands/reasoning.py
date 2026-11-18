import questionary

from zero_harness import config
from zero_harness.models import listing
from zero_harness.ui.notes import note

DESCRIPTION = "Set reasoning: /reasoning <level>, or /reasoning alone for a menu. Levels depend on the model."


def complete(words: list[str]) -> list[str]:
    return [] if words else listing.efforts(config.get("model"))


def default(model: str) -> str | None:
    """The current level if the model supports it, else medium, else its lowest. None if it doesn't reason."""
    levels = listing.efforts(model)
    if not levels:
        return None
    current = config.get("effort")
    return current if current in levels else "medium" if "medium" in levels else levels[0]


async def pick(model: str) -> str | None:
    """Ask for a reasoning level for `model`. Returns its default if the user cancels, None if it doesn't reason."""
    levels = listing.efforts(model)
    if not levels:
        return None
    choice = await questionary.select("reasoning:", choices=levels, default=default(model)).ask_async()
    return choice or default(model)


async def run(history: list, args: str) -> None:
    model = config.get("model")
    levels = listing.efforts(model)
    if not levels:
        note(f"{model} doesn't reason.")
        return
    level = args or await pick(model)
    if level not in levels:
        note(f"unknown level {level!r} for {model}. Use one of: {', '.join(levels)}")
        return
    config.update("effort", level)
    note(f"reasoning: {level} (saved)")
