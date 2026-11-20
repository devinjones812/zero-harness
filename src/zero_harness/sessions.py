"""The current conversation's file in ~/.zero/sessions/: history, cost, title, /self-improve runs, and the screen text.
main saves it after each turn and each command; /resume loads one."""

import json
from datetime import datetime
from pathlib import Path

from zero_harness import config, usage
from zero_harness.ui import notes

DIR = config.HOME / "sessions"
DIR.mkdir(parents=True, exist_ok=True)
STAMP = "%Y-%m-%d_%H-%M-%S"

current = DIR / f"{datetime.now():{STAMP}}.json"
title = ""
# /self-improve runs in this session: {"at": history length, "folder": ..., "checkpoint": ...}
improved: list[dict] = []
_screen = ""  # Output carried over from a previous process, since the last capture.


def screen() -> str:
    """Plain text of what the user saw, with each link's URL after its label."""
    with notes.console._record_buffer_lock:
        segments = [segment for segment in notes.console._record_buffer if not segment.control]
    parts, link = [], None
    for segment in segments:
        new = segment.style.link if segment.style else None
        if link and new != link:
            parts.append(f" ({link})")
        link = new
        parts.append(segment.text)
    return _screen + "".join(parts) + (f" ({link})" if link else "")


def clear_screen() -> None:
    global _screen
    _screen = ""
    notes.console.export_text()


def save(history: list) -> None:
    """Write history, usage, review checkpoints, and uncaptured terminal output."""
    if not history:
        return
    data = {
        "title": title,
        "cost": usage.cost,
        "input_tokens": usage.input_tokens,
        "improved": improved,
        "screen": screen(),
        "history": history,
    }
    current.write_text(json.dumps(data, indent=2) + "\n")


def new() -> None:
    """Start a fresh session file with zero cost. The old session stays saved."""
    global current, title, improved
    current, title, improved = DIR / f"{datetime.now():{STAMP}}.json", "", []
    clear_screen()
    usage.cost, usage.priced, usage.input_tokens = 0.0, True, 0


def load(path: Path) -> list:
    """Restore the session and its last measured context, if saved."""
    global current, title, improved, _screen
    data = json.loads(path.read_text())
    current, title, improved = path, data["title"], data.get("improved", [])
    _screen = data.get("screen", "")
    usage.cost, usage.input_tokens = data.get("cost", 0.0), data.get("input_tokens")
    return data["history"]


def label(path: Path) -> str:
    started = datetime.strptime(path.stem, STAMP)
    return f"{json.loads(path.read_text())['title'] or '(untitled)'}  ({started:%b %d %H:%M})"


def all_sessions() -> list[Path]:
    """Return saved sessions, newest first."""
    return sorted(DIR.glob("*.json"), reverse=True)
