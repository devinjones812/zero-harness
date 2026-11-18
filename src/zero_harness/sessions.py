import json
from datetime import datetime
from pathlib import Path

from zero_harness import config, usage

DIR = config.HOME / "sessions"
DIR.mkdir(parents=True, exist_ok=True)
STAMP = "%Y-%m-%d_%H-%M-%S"

current = DIR / f"{datetime.now():{STAMP}}.json"
title = ""


def save(history: list) -> None:
    """Write history, title, and cost so far to the current session file."""
    if not history:
        return
    data = {"title": title, "cost": usage.cost, "history": history}
    current.write_text(json.dumps(data, indent=2) + "\n")


def load(path: Path) -> list:
    """Make `path` the current session and return its history. Context size is unknown until the next call."""
    global current, title
    data = json.loads(path.read_text())
    current, title = path, data["title"]
    usage.cost, usage.input_tokens = data.get("cost", 0.0), 0
    return data["history"]


def label(path: Path) -> str:
    started = datetime.strptime(path.stem, STAMP)
    return f"{json.loads(path.read_text())['title'] or '(untitled)'}  ({started:%b %d %H:%M})"


def all_sessions() -> list[Path]:
    """Return saved sessions, newest first."""
    return sorted(DIR.glob("*.json"), reverse=True)
