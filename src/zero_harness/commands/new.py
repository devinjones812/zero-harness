from zero_harness import jobs, sessions
from zero_harness.tools import agent
from zero_harness.ui.notes import note

DESCRIPTION = "start a new session"


def run(history: list, args: str) -> None:
    history.clear()
    sessions.new()
    jobs.detach()
    agent.cancel_all()  # their reports belong to the old session
    note("new session")
