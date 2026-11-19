import asyncio
import json

import pytest

from zero_harness import config, usage
from zero_harness.models import registry
from zero_harness.models.reply import Reply, Usage
from zero_harness.tools import subagent
from zero_harness.ui import user_input


def reply(*output):
    return Reply(model="m", output=list(output), usage=Usage(input_tokens=1000, cached_tokens=0, output_tokens=100))


def call(name, call_id, **args):
    return {"type": "function_call", "call_id": call_id, "name": name, "arguments": json.dumps(args)}


def message(text):
    return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}


def test_asks_once_for_the_smart_model_and_saves_it(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(config, "update", lambda key, value: config.saved.__setitem__(key, value))
    registry.account["anthropic"] = {"claude-haiku-5-5", "claude-opus-5-5"}
    preselected = []

    async def picker(default):
        preselected.append(default)
        return default

    monkeypatch.setattr(subagent.model_command, "pick_configured", picker)

    async def two_at_once():
        return await asyncio.gather(subagent.pick("smart"), subagent.pick("smart"))

    assert asyncio.run(two_at_once()) == ["anthropic/claude-opus-5-5"] * 2
    assert preselected == ["anthropic/claude-opus-5-5"]  # one picker for both
    assert asyncio.run(subagent.pick("current")) == "anthropic/claude-haiku-5-5"


def test_exact_model_from_another_provider(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    registry.account["openai"] = {"gpt-6.2-astra"}
    assert asyncio.run(subagent.pick("openai/gpt-6.2-astra")) == "openai/gpt-6.2-astra"
    with pytest.raises(ValueError, match="no model 'gpt-typo'"):
        asyncio.run(subagent.pick("openai/gpt-typo"))
    with pytest.raises(ValueError, match="no API key for anthropic"):
        asyncio.run(subagent.pick("anthropic/claude-opus-5-5"))


def test_subagent_tools_never_include_agent():
    names = {tool.SCHEMA["name"] for tool in subagent.READ_ONLY}
    assert names == {"read_file", "grep", "web_search", "web_fetch"}
    assert {tool.SCHEMA["name"] for tool in subagent.EDITING} == names | {"edit_file", "bash"}


def test_starts_in_the_background_and_reports_when_done(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    config.saved["smart_model"] = "anthropic/claude-opus-5-5"
    replies = iter([reply(call("grep", "1", pattern="x")), reply(message("found it at a.py:3"))])
    seen, reports, go = [], [], asyncio.Event()

    async def fake_call(*, model, history, tools, **_):
        await go.wait()
        seen.append((model, [schema["name"] for schema in tools], len(history)))
        return next(replies)

    monkeypatch.setattr(registry, "call", fake_call)
    monkeypatch.setattr(subagent.grep, "run", lambda pattern: "a.py:3:x")
    monkeypatch.setattr(subagent, "on_finish", reports.append)
    monkeypatch.setattr(usage, "cost", 0.0)

    async def scenario():
        started = await subagent.run("find x", model="smart")
        assert started.startswith("started subagent") and not reports
        await asyncio.sleep(0)
        assert [state for state, _ in user_input.subagents.values()] == ["working"]
        go.set()
        await asyncio.gather(*subagent.tasks.values())

    asyncio.run(scenario())
    assert seen[0] == ("anthropic/claude-opus-5-5", ["read_file", "grep", "web_search", "web_fetch"], 1)
    assert seen[1][2] == 3  # task, grep call, grep output
    assert len(reports) == 1 and "find x" in reports[0] and reports[0].endswith("found it at a.py:3")
    assert not user_input.subagents and not subagent.tasks
    assert usage.cost > 0


def test_subagents_run_together_and_cancel_without_reporting(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    both_running, reports = asyncio.Barrier(2), []

    async def fake_call(**_):
        await asyncio.wait_for(both_running.wait(), timeout=1)  # times out unless the two run together
        await asyncio.sleep(10)

    monkeypatch.setattr(registry, "call", fake_call)
    monkeypatch.setattr(subagent, "on_finish", reports.append)

    async def scenario():
        await subagent.run("one")
        await subagent.run("two")
        await asyncio.sleep(0.1)
        assert subagent.cancel_all() == 2
        await asyncio.gather(*subagent.tasks.values(), return_exceptions=True)

    asyncio.run(scenario())
    assert reports == [] and not subagent.tasks
