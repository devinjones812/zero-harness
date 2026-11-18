from zero_harness import sessions
from zero_harness.ui.notes import note

DESCRIPTION = "Rename this session. /title shows the current title; /title <new title> renames it."


def run(history: list, args: str) -> None:
    if args:
        sessions.title = args
    note(f"title: {sessions.title or '(untitled)'}")
