import asyncio

import pytest

from zero_harness import catalog, config, errors
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


def test_smartest_skips_unversioned_aliases(monkeypatch):
    daybreak = {"family": "claude", "released": "2026-11-01", "agentic": True, "cost": {"input": 12, "output": 75}}
    monkeypatch.setitem(catalog.providers["anthropic"], "claude-daybreak-latest", daybreak)
    assert listing.smartest("anthropic") == "claude-opus-5-5"


def test_newest_of_a_family():
    assert listing.newest("anthropic", "claude-opus") == "claude-opus-5-5"
    assert listing.newest("anthropic", "claude-old") is None  # stale
    assert listing.newest("anthropic", "claude-sonnet") is None


class RateLimitError(Exception):
    """Stands in for both SDKs' RateLimitError, which zero matches by name."""


def fake_api(monkeypatch, failures):
    """Point registry at an API that raises each of `failures`, then answers. Returns the call count."""
    calls = []

    async def call(*_, **__):
        calls.append(1)
        if len(calls) <= len(failures):
            raise failures[len(calls) - 1]
        return "reply"

    monkeypatch.setattr(registry, "api", lambda name: type("API", (), {"call": staticmethod(call)}))
    monkeypatch.setattr(registry, "client", lambda name: None)
    sleep = asyncio.sleep
    monkeypatch.setattr(registry.asyncio, "sleep", lambda seconds: sleep(0))
    return calls


def test_waits_for_a_free_request_slot(monkeypatch):
    busy = RateLimitError("Number of concurrent connections has exceeded your rate limit.")
    calls = fake_api(monkeypatch, [busy, busy])
    assert asyncio.run(registry.call(instructions="", history=[], model="anthropic/claude-opus-5-5")) == "reply"
    assert len(calls) == 3


def test_gives_up_with_a_clear_message(monkeypatch):
    busy = RateLimitError("Number of concurrent connections has exceeded your rate limit.")
    fake_api(monkeypatch, [busy] * 100)
    monkeypatch.setattr(registry, "SLOT_WAIT", 0)
    with pytest.raises(errors.RateLimited, match="only a few requests at once"):
        asyncio.run(registry.call(instructions="", history=[], model="anthropic/claude-opus-5-5"))
    fake_api(monkeypatch, [RateLimitError("tokens per minute exceeded")])
    with pytest.raises(errors.RateLimited, match="per minute"):
        asyncio.run(registry.call(instructions="", history=[], model="anthropic/claude-opus-5-5"))


def test_complete_keeps_tool_choice_for_the_cache_and_retries_if_a_tool_is_called(monkeypatch):
    from zero_harness import llm
    from zero_harness.models.reply import Reply, Usage

    config.saved["model"] = "anthropic/claude-opus-5-5"
    used = Usage(input_tokens=10, cached_tokens=0, output_tokens=1)
    tool_call = Reply("m", [{"type": "function_call", "call_id": "1", "name": "grep", "arguments": "{}"}], used)
    text = Reply("m", [{"type": "message", "content": [{"type": "output_text", "text": "summary"}]}], used)
    replies, choices = iter([text, tool_call, text]), []

    async def call(*, tool_choice=None, **_):
        choices.append(tool_choice)
        return next(replies)

    monkeypatch.setattr(llm.registry, "call", call)
    assert asyncio.run(llm.complete([], [])) == "summary"
    assert asyncio.run(llm.complete([], [])) == "summary"
    assert choices == [None, None, "none"]  # the normal choice first; tools off only after a tool call


def test_level_sends_only_what_the_model_offers():
    assert listing.level("anthropic/claude-opus-5-5", "high") == "high"
    assert listing.level("anthropic/claude-opus-5-5", "xhigh") is None  # not offered: the provider's default
    assert listing.level("anthropic/claude-haiku-5-5", "low") is None  # doesn't reason


def test_cheapest_and_efforts():
    assert listing.cheapest("anthropic") == "claude-haiku-5-5"
    assert listing.efforts("anthropic/claude-opus-5-5") == ["low", "medium", "high"]
    assert listing.efforts("anthropic/claude-opus-5") == listing.EFFORTS  # reasons, levels unknown
    assert listing.efforts("anthropic/claude-haiku-5-5") == []
