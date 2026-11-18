import questionary

from zero_harness import sessions
from zero_harness.ui.notes import note

DESCRIPTION = "Pick a saved session and continue it."


async def run(history: list, args: str) -> None:
    paths = [path for path in sessions.all_sessions() if path != sessions.current]
    if not paths:
        note("no saved sessions")
        return
    choices = [questionary.Choice(sessions.label(path), value=path) for path in paths]
    path = await questionary.select("session:", choices=choices).ask_async()
    if path:
        history[:] = sessions.load(path)
        note(f"resumed: {sessions.title}")
