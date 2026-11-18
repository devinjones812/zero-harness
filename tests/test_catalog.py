import json
import os
import time

import httpx
import pytest

from zero_harness import catalog

DAY = catalog.DAY
PROVIDERS = {"p": {"m": {"cost": None}}}


@pytest.fixture
def cache(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    monkeypatch.setattr(catalog, "PATH", path)
    monkeypatch.setattr(catalog, "providers", {})
    return path


def write(path, days_old, version=catalog.VERSION):
    path.write_text(json.dumps({"version": version, "providers": PROVIDERS}))
    then = time.time() - days_old * DAY
    os.utime(path, (then, then))


def offline(monkeypatch):
    def fail():
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(catalog, "refresh", fail)


def test_fresh_cache_skips_the_fetch(cache, monkeypatch):
    write(cache, days_old=0.5)
    monkeypatch.setattr(catalog, "refresh", lambda: pytest.fail("fetched a fresh cache"))
    assert catalog.load() is None
    assert catalog.providers == PROVIDERS


def test_old_format_refreshes(cache, monkeypatch):
    write(cache, days_old=0, version=1)
    fetched = {"version": catalog.VERSION, "providers": {"new": {}}}
    monkeypatch.setattr(catalog, "refresh", lambda: fetched)
    assert catalog.load() is None
    assert catalog.providers == {"new": {}}


def test_failed_refresh_keeps_the_old_cache(cache, monkeypatch):
    write(cache, days_old=3)
    offline(monkeypatch)
    assert catalog.load() is None
    assert catalog.providers == PROVIDERS


def test_warns_when_over_a_week_old(cache, monkeypatch):
    write(cache, days_old=9)
    offline(monkeypatch)
    assert "9 days old" in catalog.load()


def test_warns_when_missing(cache, monkeypatch):
    offline(monkeypatch)
    assert "could not reach" in catalog.load()
    assert catalog.providers == {}


def test_entry_keeps_family_and_reasoning_levels():
    model = {
        "id": "m",
        "family": "f",
        "reasoning": True,
        "reasoning_options": [{"type": "toggle"}, {"type": "effort", "values": ["low", "high"]}],
        "tool_call": True,
        "limit": {"context": 5},
    }
    assert catalog.entry(model)["agentic"]
    assert not catalog.entry(model | {"modalities": {"output": ["text", "audio"]}})["agentic"]
    assert catalog.entry(model)["efforts"] == ["low", "high"]
    assert catalog.entry(model)["family"] == "f"
    assert catalog.entry(model | {"reasoning": False})["efforts"] == []
    assert catalog.entry({"id": "x", "reasoning": True})["efforts"] is None
