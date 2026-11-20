import asyncio
import json

import pytest

from zero_harness import config, usage
from zero_harness.models import registry, tiers
from zero_harness.models.reply import Reply, Usage
from zero_harness.tools import subagent
from zero_harness.tools.subagent import models as subagent_models
from zero_harness.ui import pickers, user_input


@pytest.fixture(autouse=True)
def no_confirmed_models(monkeypatch, tmp_path):
    monkeypatch.setattr(subagent_models, "confirmed", {})
    monkeypatch.setattr(subagent.permissions, "APPROVALS", tmp_path / "approvals.jsonl")


def reply(*output):
    return Reply(model="m", output=list(output), usage=Usage(input_tokens=1000, cached_tokens=0, output_tokens=100))


def call(name, call_id, **args):
    return {"type": "function_call", "call_id": call_id, "name": name, "arguments": json.dumps(args)}


def message(text):
    return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}


class Select:
    """Stands in for questionary.select, answering with each of `answers` in turn."""

    def __init__(self, answers):
        self.answers, self.asked = iter(answers), 0

    def __call__(self, *_, **__):
        self.asked += 1
        return self

    async def ask_async(self):
        return next(self.answers)


def answer(text):
    async def ask(prompt):
        return text

    return ask


def test_first_use_confirms_both_tiers_once_and_saves_them(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(config, "update", lambda key, value: config.saved.__setitem__(key, value))
    registry.account["anthropic"] = {"claude-haiku-5-5", "claude-opus-5-5"}
    monkeypatch.setitem(tiers.TIERS["fast"]["families"], "anthropic", "claude-haiku")
    select = Select([pickers.USE])
    monkeypatch.setattr(pickers.questionary, "select", select)

    async def two_at_once():
        return await asyncio.gather(subagent_models.pick("smart"), subagent_models.pick("fast"))

    # claude-fable is not in this catalog, so smart goes by price. Haiku 5.5 doesn't reason here: no level.
    assert asyncio.run(two_at_once()) == [("anthropic/claude-opus-5-5", "medium"), ("anthropic/claude-haiku-5-5", None)]
    assert select.asked == 1  # one screen for both
    assert config.saved["smart_model"] == "anthropic/claude-opus-5-5"
    assert asyncio.run(subagent_models.pick("current")) == ("anthropic/claude-haiku-5-5", None)


def test_ctrl_c_in_setup_stops_the_turn_and_saves_nothing(monkeypatch):
    config.saved["model"] = "anthropic/claude-opus-5-5"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    registry.account["anthropic"] = {"claude-haiku-5-5", "claude-opus-5-5"}
    monkeypatch.setattr(pickers.questionary, "select", Select([None]))  # questionary's answer to Ctrl+C
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(subagent.run("find x"))
    assert "fast_model" not in config.saved and not subagent.tasks


def test_exact_model_opens_the_picker_on_it_once(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    registry.account["openai"] = {"gpt-6.2-astra"}
    starts = []

    async def picker(model, level):
        starts.append(model)
        return model or "openai/gpt-6.2-astra", "low"

    monkeypatch.setattr(pickers, "pick_subagent", picker)
    assert asyncio.run(subagent_models.pick("openai/gpt-6.2-astra")) == ("openai/gpt-6.2-astra", "low")
    assert asyncio.run(subagent_models.pick("openai/gpt-6.2-astra")) == ("openai/gpt-6.2-astra", "low")
    asyncio.run(subagent_models.pick("openai/astra-6.2"))
    asyncio.run(subagent_models.pick("venice/model"))
    # Confirmed once. A wrong guess opens on the closest model, an unknown provider on nothing.
    assert starts == ["openai/gpt-6.2-astra", "openai/gpt-6.2-astra", None]


def test_ctrl_c_in_the_exact_model_picker_stops_the_turn(monkeypatch):
    config.saved["model"] = "anthropic/claude-haiku-5-5"

    async def cancel(model, level):
        return None

    monkeypatch.setattr(pickers, "pick_subagent", cancel)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(subagent_models.pick("anthropic/claude-opus-5-5"))


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
    monkeypatch.setattr(user_input, "ask", answer("y"))
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


def test_defaults_to_the_fast_tier():
    config.saved.update(model="anthropic/claude-opus-5-5", fast_model="anthropic/claude-haiku-5-5", fast_effort=None)
    assert asyncio.run(subagent_models.pick("fast")) == ("anthropic/claude-haiku-5-5", None)
    assert asyncio.run(subagent_models.pick("current")) == ("anthropic/claude-opus-5-5", "medium")


def test_declined_smart_subagent_does_not_start(monkeypatch):
    config.saved.update(model="anthropic/claude-haiku-5-5", smart_model="anthropic/claude-opus-5-5")
    monkeypatch.setattr(user_input, "ask", answer("not yet, try the logs"))
    result = asyncio.run(subagent.run("why does x fail", model="smart"))
    assert result.startswith("error: user denied this and said: not yet, try the logs")
    assert not subagent.tasks


def test_editing_subagents_refuse_fast():
    assert asyncio.run(subagent.run("change a.py", model="fast", edit=True)).startswith("error: editing subagents")


def test_subagents_run_together_and_cancel_without_reporting(monkeypatch):
    config.saved.update(model="anthropic/claude-haiku-5-5", fast_model="anthropic/claude-haiku-5-5")
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
