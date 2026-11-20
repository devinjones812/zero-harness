from pathlib import Path

turns: list[dict[Path, bytes | None]] = []


def start() -> None:
    """Begin a checkpoint for the next turn."""
    turns.append({})


def record(path: str) -> None:
    """Save a file's content before its first edit this turn. None means the file did not exist."""
    file = Path(path).resolve()
    if turns and file not in turns[-1]:
        turns[-1][file] = file.read_bytes() if file.exists() else None


def undo() -> list[Path]:
    """Restore the files from the most recent turn that edited any. Returns the restored files."""
    while turns:
        files = turns.pop()
        for file, content in files.items():
            if content is None:
                file.unlink(missing_ok=True)
            else:
                file.write_bytes(content)
        if files:
            return list(files)
    return []
