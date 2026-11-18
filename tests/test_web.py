import pytest

from zero_harness import config
from zero_harness.web import anthropic, backend, openai, parallel


def test_search_follows_the_model(monkeypatch):
    config.saved["model"] = "openai/gpt-6.2-sol"
    assert backend.choose() is openai
    config.saved["model"] = "anthropic/claude-opus-5-5"
    assert backend.choose() is anthropic
    config.saved |= {"model": "venice/deepseek", "providers": {"venice": {"key_env": "V"}}}
    with pytest.raises(RuntimeError, match="Parallel"):
        backend.choose()
    monkeypatch.setenv("PARALLEL_API_KEY", "x")
    assert backend.choose() is parallel


def test_parallel_when_chosen(monkeypatch):
    config.saved |= {"model": "openai/gpt-6.2-sol", "search_provider": "parallel"}
    assert backend.choose() is openai  # no key yet
    monkeypatch.setenv("PARALLEL_API_KEY", "x")
    assert backend.choose() is parallel
