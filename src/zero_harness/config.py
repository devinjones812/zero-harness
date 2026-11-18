import json
from pathlib import Path

HOME = Path.home() / ".zero"
PATH = HOME / "config.json"

DEFAULTS = {
    "model": "gpt-6.2-astra",
    "effort": "medium",
    "max_tool_rounds": 50,
    "auto": True,
}

saved = json.loads(PATH.read_text()) if PATH.exists() else {}


def get(key: str):
    """Return the saved value, or the default if the user never set it."""
    return saved.get(key, DEFAULTS[key])


def update(key: str, value) -> None:
    """Set a value and write config.json. Only user-set keys are saved, so default changes still apply."""
    saved[key] = value
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(saved, indent=2) + "\n")
