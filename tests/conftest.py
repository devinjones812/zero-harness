import datetime

import pytest

from zero_harness import catalog, config
from zero_harness.models import listing, registry

KEYS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PARALLEL_API_KEY", "TYPESAFE_API_KEY"]


def model(family, released, cost=None, efforts=(), agentic=True):
    return {"family": family, "released": released, "agentic": agentic, "cost": cost, "efforts": efforts}


CATALOG = {
    "anthropic": {
        "claude-opus-5-5": model("claude-opus", "2026-09-22", {"input": 4, "output": 20}, ["low", "medium", "high"]),
        "claude-opus-5": model("claude-opus", "2026-03-01", {"input": 5, "output": 25}, None),
        "claude-haiku-5-5": model("claude-haiku", "2026-10-07", {"input": 0.1, "output": 0.5}, []),
        "claude-embed": model("embed", "2026-11-01", agentic=False),
        "claude-old": model("claude-old", "2020-01-01", {"input": 0.01, "output": 0.1}, []),
    }
}


class Today(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 18)


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    """No saved config, no real keys, a small fixed catalog, and a fixed date."""
    monkeypatch.setattr(config, "saved", {})
    monkeypatch.setattr(catalog, "providers", CATALOG)
    monkeypatch.setattr(registry, "account", {})
    monkeypatch.setattr(listing, "date", Today)
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
