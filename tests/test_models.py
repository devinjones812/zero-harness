import pytest

from zero_harness import config
from zero_harness.models import listing, registry


def test_split():
    config.saved["providers"] = {"venice": {"key_env": "V"}}
    assert registry.split("venice/deepseek") == ("venice", "deepseek")
    assert registry.split("anthropic/claude-opus-5-5") == ("anthropic", "claude-opus-5-5")
    assert registry.split("gpt-6.2-sol") == ("openai", "gpt-6.2-sol")  # older configs


def test_split_rejects_a_removed_provider():
    with pytest.raises(ValueError, match="unknown provider 'venice'"):
        registry.split("venice/deepseek")


def test_new_key_gets_a_new_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "one")
    first = registry.client("openai")
    assert registry.client("openai") is first
    monkeypatch.setenv("OPENAI_API_KEY", "two")
    assert registry.client("openai") is not first


def test_latest_of_each_current_family_newest_first(monkeypatch):
    assert listing.latest("anthropic") == ["claude-haiku-5-5", "claude-opus-5-5"]  # claude-old is stale
    assert listing.latest("openai") == []
    monkeypatch.setattr(listing, "CURRENT_DAYS", 0)
    assert listing.latest("anthropic") == ["claude-haiku-5-5", "claude-opus-5-5", "claude-old"]  # nothing recent


def test_lists_only_models_the_key_can_use():
    registry.account["anthropic"] = {"claude-opus-5-5", "claude-opus-5"}
    assert listing.latest("anthropic") == ["claude-opus-5-5"]
    assert listing.every("anthropic") == ["claude-opus-5-5", "claude-opus-5"]


def test_cheapest_and_efforts():
    assert listing.cheapest("anthropic") == "claude-haiku-5-5"
    assert listing.efforts("anthropic/claude-opus-5-5") == ["low", "medium", "high"]
    assert listing.efforts("anthropic/claude-opus-5") == listing.EFFORTS  # reasons, levels unknown
    assert listing.efforts("anthropic/claude-haiku-5-5") == []
