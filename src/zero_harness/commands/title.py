from zero_harness import sessions
from zero_harness.ui.notes import note

DESCRIPTION = "rename session"


def run(history: list, args: str) -> None:
    if args:
        sessions.title = args
    note(f"title: {sessions.title or '(untitled)'}")
