from zero_harness import jobs, sessions
from zero_harness.ui.notes import note

DESCRIPTION = "Start a new session. The current one stays saved for /resume."


def run(history: list, args: str) -> None:
    history.clear()
    sessions.new()
    jobs.detach()
    note("new session")
