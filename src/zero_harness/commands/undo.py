import os

from zero_harness import checkpoints
from zero_harness.ui.notes import note

DESCRIPTION = "undo last edits"


def run(history: list, args: str) -> None:
    files = checkpoints.undo()
    if not files:
        note("nothing to undo")
        return
    names = ", ".join(os.path.relpath(file) for file in files)
    note(f"restored: {names}")
    history.append(
        {
            "role": "user",
            "content": f"(I undid your edits to: {names}. They are back to how they were before that turn.)",
        }
    )
