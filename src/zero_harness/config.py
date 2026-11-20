import json
import os
from pathlib import Path

from dotenv import load_dotenv

HOME = Path.home() / ".zero"
PATH = HOME / "config.json"

load_dotenv(HOME / ".env")

DEFAULTS = {
    "model": None,  # the user picks one on first run
    "effort": "medium",
    "max_tool_rounds": 50,
    "smart_model": None,  # subagent models and reasoning levels; the user confirms them the first time
    "smart_effort": None,
    "fast_model": None,
    "fast_effort": None,
    "providers": {},
}
# Command reviewers for auto-review mode and the keys they need, in default order.
REVIEWERS = {"openai": "OPENAI_API_KEY", "jev": "TYPESAFE_API_KEY"}

saved = json.loads(PATH.read_text()) if PATH.exists() else {}
if saved.get("mode") == "auto":  # renamed
    saved["mode"] = "auto-review"


def get(key: str):
    """Return the saved value, or the default if the user never set it."""
    if key in saved:
        return saved[key]
    if key == "mode":
        return "auto-review" if reviewer() else "ask"
    return DEFAULTS[key]


def reviewer() -> str | None:
    """The command reviewer for auto-review: "approval_provider" if its key is set, else the first with a key."""
    chosen = saved.get("approval_provider")
    if chosen in REVIEWERS:
        return chosen if os.getenv(REVIEWERS[chosen]) else None
    return next((name for name, env in REVIEWERS.items() if os.getenv(env)), None)


def update(key: str, value) -> None:
    """Set a value and write config.json. Only user-set keys are saved, so default changes still apply."""
    saved[key] = value
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(saved, indent=2) + "\n")
