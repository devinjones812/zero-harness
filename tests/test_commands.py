import asyncio

from prompt_toolkit.document import Document

from zero_harness import config
from zero_harness.commands import mode, registry
from zero_harness.ui.user_input import CommandCompleter


def test_refuses_auto_review_without_a_reviewer():
    asyncio.run(mode.run([], "auto-review"))
    assert "mode" not in config.saved


def test_tab_completion():
    completer = CommandCompleter(registry.options())

    def complete(text):
        return [item.text for item in completer.get_completions(Document(text), None)]

    assert complete("/model ") == ["openai", "anthropic"]
    assert complete("/model anthropic ") == ["claude-haiku-5-5", "claude-opus-5-5"]
    assert complete("/model anthropic claude-opus-5-5 ") == []
    assert complete("/mode ") == mode.MODES
    assert complete("/mode ask ") == []
    config.saved["model"] = "anthropic/claude-opus-5-5"
    assert complete("/reasoning ") == ["low", "medium", "high"]
    assert complete("/mo") == ["/model", "/mode"]
    names = completer.get_completions(Document("/"), None)
    assert all(item.display_meta_text for item in names)
