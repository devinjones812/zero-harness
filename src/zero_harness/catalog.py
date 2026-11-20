"""Model prices, context windows, families, and reasoning levels from models.dev, a public catalog of AI providers.
zero keeps the fields it needs in ~/.zero/catalog.json and refreshes the file at startup once a day.
If a refresh fails, the old file stays in use."""

import json
import time

import httpx

from zero_harness import config

URL = "https://models.dev/api.json"
PATH = config.HOME / "catalog.json"
VERSION = 3  # bump when the kept fields change, so old caches refresh
DAY = 24 * 60 * 60
STALE_AFTER_DAYS = 7

# {"<models.dev provider id>": {"<model id>": {"cost", "context", "agentic", "released", "family", "efforts"}}}
providers: dict = {}


def load() -> str | None:
    """Refresh the cache if it is over a day old, then load it. Returns a warning if the data is old or missing."""
    cached = json.loads(PATH.read_text()) if PATH.exists() else {}
    age = time.time() - PATH.stat().st_mtime if cached.get("version") == VERSION else float("inf")
    if age > DAY:
        try:
            cached = refresh()
            age = 0
        except httpx.HTTPError, ValueError, KeyError:
            pass
    if cached.get("version") != VERSION:
        return "[catalog] could not reach models.dev, so model lists, prices, and context sizes are limited."
    providers.update(cached["providers"])
    if age > STALE_AFTER_DAYS * DAY:
        return f"[catalog] model data is {age / DAY:.0f} days old: could not reach models.dev to update it."
    return None


def refresh() -> dict:
    data = httpx.get(URL, timeout=5).raise_for_status().json()
    kept = {
        "version": VERSION,
        "providers": {
            provider_id: {model_id: entry(model) for model_id, model in provider["models"].items()}
            for provider_id, provider in data.items()
        },
    }
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(kept))
    temporary.replace(PATH)
    return kept


def entry(model: dict) -> dict:
    efforts = next(
        (option["values"] for option in model.get("reasoning_options", []) if option["type"] == "effort"), None
    )
    return {
        "cost": model.get("cost"),
        "context": model.get("limit", {}).get("context"),
        # Can run zero's tool loop: calls tools and answers in text. Speech models output audio and need other APIs.
        "agentic": model.get("tool_call", False) and "audio" not in model.get("modalities", {}).get("output", []),
        "released": model.get("release_date", ""),
        "family": model.get("family") or model["id"],
        # None: reasoning with unknown levels. []: no reasoning.
        "efforts": efforts if model.get("reasoning") else [],
    }


def model(provider_id: str, model_id: str) -> dict:
    """The catalog entry for a model, or {} if models.dev doesn't list it."""
    return providers.get(provider_id, {}).get(model_id, {})
