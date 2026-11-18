import json
from datetime import datetime
from pathlib import Path

from zero_harness import config, usage

DIR = config.HOME / "sessions"
DIR.mkdir(parents=True, exist_ok=True)
STAMP = "%Y-%m-%d_%H-%M-%S"

current = DIR / f"{datetime.now():{STAMP}}.json"
title = ""
# /self-improve runs in this session: {"at": history length, "folder": ..., "checkpoint": ...}
improved: list[dict] = []


def save(history: list) -> None:
    """Write history, title, usage, and /self-improve runs to the current session file."""
    if not history:
        return
    data = {
        "title": title,
        "cost": usage.cost,
        "input_tokens": usage.input_tokens,
        "improved": improved,
        "history": history,
    }
    current.write_text(json.dumps(data, indent=2) + "\n")


def new() -> None:
    """Start a fresh session file with zero cost. The old session stays saved."""
    global current, title, improved
    current, title, improved = DIR / f"{datetime.now():{STAMP}}.json", "", []
    usage.cost, usage.priced, usage.input_tokens = 0.0, True, 0


def load(path: Path) -> list:
    """Restore the session and its last measured context, if saved."""
    global current, title, improved
    data = json.loads(path.read_text())
    current, title, improved = path, data["title"], data.get("improved", [])
    usage.cost, usage.input_tokens = data.get("cost", 0.0), data.get("input_tokens")
    return data["history"]


def label(path: Path) -> str:
    started = datetime.strptime(path.stem, STAMP)
    return f"{json.loads(path.read_text())['title'] or '(untitled)'}  ({started:%b %d %H:%M})"


def all_sessions() -> list[Path]:
    """Return saved sessions, newest first."""
    return sorted(DIR.glob("*.json"), reverse=True)
