import asyncio

from zero_harness import config
from zero_harness.commands import mode, registry


def test_refuses_auto_review_without_a_reviewer():
    asyncio.run(mode.run([], "auto-review"))
    assert "mode" not in config.saved


def test_tab_completion():
    complete = registry.options()
    assert complete["model"]([]) == ["openai", "anthropic"]
    assert complete["model"](["anthropic"]) == ["claude-haiku-5-5", "claude-opus-5-5"]
    assert complete["model"](["anthropic", "claude-opus-5-5"]) == []
    assert complete["mode"]([]) == mode.MODES
    assert complete["mode"](["ask"]) == []
    config.saved["model"] = "anthropic/claude-opus-5-5"
    assert complete["reasoning"]([]) == ["low", "medium", "high"]
