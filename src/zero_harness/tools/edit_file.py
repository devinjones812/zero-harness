from zero_harness import checkpoints, workdir
from zero_harness.permissions import approve_edit
from zero_harness.ui.notes import diff

SCHEMA = {
    "type": "function",
    "name": "edit_file",
    "description": (
        "Replace old_text with new_text in a file. old_text must appear exactly once. "
        "To create a new file, use an empty old_text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    },
}


async def run(path: str, old_text: str, new_text: str) -> str:
    file = workdir.resolve(path)
    if old_text == "":
        if file.exists():
            return "error: file exists. Give old_text to edit it."
        content = new_text
    else:
        content = file.read_text()
        count = content.count(old_text)
        if count != 1:
            return f"error: old_text found {count} times, must be exactly 1"
        content = content.replace(old_text, new_text)

    in_worktree = workdir.tree.get() is not None
    if not in_worktree:  # a subagent's edits show as one change set when they merge back
        diff(old_text, new_text)
    if denied := await approve_edit(str(file)):
        return denied
    if not in_worktree:  # /undo covers the user's files; worktrees are thrown away
        checkpoints.record(str(file))
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)
    return "ok"
