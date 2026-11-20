from zero_harness import config
from zero_harness.models import listing
from zero_harness.ui import pickers
from zero_harness.ui.notes import note

DESCRIPTION = "set reasoning level"


def complete(words: list[str]) -> list[str]:
    return [] if words else listing.efforts(config.get("model"))


async def run(history: list, args: str) -> None:
    model = config.get("model")
    levels = listing.efforts(model)
    if not levels:
        note(f"{model} doesn't reason.")
        return
    level = args or await pickers.pick_level(model)
    if level not in levels:
        note(f"unknown level {level!r} for {model}. Use one of: {', '.join(levels)}")
        return
    config.update("effort", level)
    note(f"reasoning: {level} (saved)")
