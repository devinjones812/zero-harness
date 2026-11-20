import questionary

from zero_harness import jobs
from zero_harness.tools.subagent import tool as subagent

DESCRIPTION = "restart, keep conversation"

requested = False


async def run(history: list, args: str) -> None:
    """Ask main to restart once the prompt closes."""
    global requested
    running = [
        f"{count} {kind}"
        for count, kind in ((jobs.running(), "background job(s)"), (len(subagent.tasks), "subagent(s)"))
        if count
    ]
    if running:
        question = f"stop {' and '.join(running)} and reload?"
        if not await questionary.confirm(question, default=False).ask_async():
            return
    requested = True
