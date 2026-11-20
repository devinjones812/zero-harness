from zero_harness import jobs, sessions
from zero_harness.tools import subagent
from zero_harness.ui import logo, user_input

DESCRIPTION = "start a new session"


def run(history: list, args: str) -> None:
    history.clear()
    sessions.new()
    jobs.detach()
    subagent.cancel_all(drop_reports=True)  # their reports belong to the old session
    user_input.clear()
    logo.welcome()
