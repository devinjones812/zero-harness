from zero_harness import context
from zero_harness.tools import registry as tools
from zero_harness.ui.notes import note

DESCRIPTION = "summarize to free context"


async def run(history: list, args: str) -> None:
    if not history:
        note("nothing to summarize")
        return
    await context.compact(history, "you ran /summarize", tools.SCHEMAS)
