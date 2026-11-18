import json
import os
from pathlib import Path

HOME = Path.home() / ".zero"
PATH = HOME / "config.json"

DEFAULTS = {
    "model": "gpt-6.2-sol",
    "effort": "medium",
    "max_tool_rounds": 50,
    "mode": "auto",
    "search_provider": "openai",
    "approval_provider": "openai",
}
OPTIONAL_PROVIDERS = {
    "search_provider": ("parallel", "PARALLEL_API_KEY"),
    "approval_provider": ("jev", "TYPESAFE_API_KEY"),
}

saved = json.loads(PATH.read_text()) if PATH.exists() else {}


def get(key: str):
    """Return the saved value, or the default if the user never set it."""
    return saved.get(key, DEFAULTS[key])


def provider(key: str) -> str:
    """Return the configured provider, checking credentials for explicit overrides."""
    alternate, env = OPTIONAL_PROVIDERS[key]
    value = get(key)
    if value not in ("openai", alternate):
        raise ValueError(f"Set {key} to openai or {alternate} in {PATH}.")
    if value == alternate and not os.getenv(env):
        raise ValueError(f"Set {env} in {HOME / '.env'} to use {alternate}.")
    return value


def update(key: str, value) -> None:
    """Set a value and write config.json. Only user-set keys are saved, so default changes still apply."""
    saved[key] = value
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(saved, indent=2) + "\n")
