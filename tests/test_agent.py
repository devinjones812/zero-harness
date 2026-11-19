import asyncio
import json

import pytest

from zero_harness import config, usage
from zero_harness.models import registry
from zero_harness.models.reply import Reply, Usage
from zero_harness.tools import agent
from zero_harness.tools import registry as tools


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

    monkeypatch.setattr(agent.model_command, "pick_configured", picker)

    async def two_at_once():
        return await asyncio.gather(agent.pick("smart"), agent.pick("smart"))

    assert asyncio.run(two_at_once()) == ["anthropic/claude-opus-5-5"] * 2
    assert preselected == ["anthropic/claude-opus-5-5"]  # one picker for both
    assert asyncio.run(agent.pick("current")) == "anthropic/claude-haiku-5-5"


def test_exact_model_from_another_provider(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    registry.account["openai"] = {"gpt-6.2-astra"}
    assert asyncio.run(agent.pick("openai/gpt-6.2-astra")) == "openai/gpt-6.2-astra"
    with pytest.raises(ValueError, match="no model 'gpt-typo'"):
        asyncio.run(agent.pick("openai/gpt-typo"))
    with pytest.raises(ValueError, match="no API key for anthropic"):
        asyncio.run(agent.pick("anthropic/claude-opus-5-5"))


def test_subagents_are_read_only_and_cannot_start_subagents():
    assert set(agent.FUNCTIONS) == {"read_file", "grep", "web_search", "web_fetch"}


def test_runs_tools_until_it_answers_and_counts_its_cost(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    config.saved["smart_model"] = "anthropic/claude-opus-5-5"
    replies = iter([reply(call("grep", "1", pattern="x")), reply(message("found it at a.py:3"))])
    seen = []

    async def fake_call(*, model, history, tools, **_):
        seen.append((model, [schema["name"] for schema in tools], len(history)))
        return next(replies)

    monkeypatch.setattr(registry, "call", fake_call)
    monkeypatch.setitem(agent.FUNCTIONS, "grep", lambda pattern: "a.py:3:x")
    monkeypatch.setattr(usage, "cost", 0.0)
    answer = asyncio.run(agent.run("find x", model="smart"))
    assert answer == "found it at a.py:3"
    assert seen[0] == ("anthropic/claude-opus-5-5", ["read_file", "grep", "web_search", "web_fetch"], 1)
    assert seen[1][2] == 3  # task, grep call, grep output
    assert usage.cost > 0


def test_subagents_run_in_parallel_and_outputs_keep_call_order(monkeypatch):
    both_running = asyncio.Barrier(2)

    async def fake_agent(task, model="current"):
        await asyncio.wait_for(both_running.wait(), timeout=1)  # times out unless the two run together
        return task

    monkeypatch.setitem(tools.FUNCTIONS, "agent", fake_agent)
    monkeypatch.setitem(tools.FUNCTIONS, "todo", lambda items: "ok")
    calls = [call("agent", "a", task="one"), call("todo", "t", items=[]), call("agent", "b", task="two")]
    outputs = asyncio.run(tools.run_all(calls))
    assert [output["output"] for output in outputs] == ["one", "ok", "two"]
