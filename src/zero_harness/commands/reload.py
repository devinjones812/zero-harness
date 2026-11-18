import questionary

from zero_harness import jobs

DESCRIPTION = "Restart zero to apply code changes, then continue this conversation."

requested = False


async def run(history: list, args: str) -> None:
    """Ask main to restart once the prompt closes."""
    global requested
    if count := jobs.running():
        question = f"stop {count} running background job(s) and reload?"
        if not await questionary.confirm(question, default=False).ask_async():
            return
    requested = True
