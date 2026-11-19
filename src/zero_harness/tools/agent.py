import asyncio

from zero_harness import config, usage
from zero_harness.models import listing, registry
from zero_harness.prompt import SUBAGENT
from zero_harness.tools import grep, read_file, runner, web_fetch, web_search
from zero_harness.ui.notes import note

# Read-only, and no agent tool: subagents can't edit, run commands, or start their own subagents.
TOOLS = [read_file, grep, web_search, web_fetch]
SCHEMAS = [tool.SCHEMA for tool in TOOLS]
FUNCTIONS = {tool.SCHEMA["name"]: tool.run for tool in TOOLS}
MAX_ROUNDS = 30
running = asyncio.Semaphore(4)  # at most this many subagents at once

SCHEMA = {
    "type": "function",
    "name": "agent",
    "description": (
        "Hand a task to a subagent with read-only tools (grep, read_file, web_search, web_fetch). It returns only "
        "its final answer. It can't see this conversation, so give it everything: the goal, relevant paths and "
        "facts, and what to return. Call agent several times in one reply to run subagents in parallel."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "A self-contained brief: goal, context, and what to return."},
            "model": {
                "type": "string",
                "enum": ["current", "smart", "fast"],
                "description": (
                    "current (default): your model. smart: the provider's most capable model, for a narrow, hard "
                    "problem. fast: its cheapest model, for simple searches."
                ),
            },
        },
        "required": ["task"],
    },
}


async def run(task: str, model: str = "current") -> str:
    chosen = pick(model)
    history = [{"role": "user", "content": task}]
    spent, text = 0.0, ""
    async with running:
        for rounds in range(1, MAX_ROUNDS + 1):
            reply = await registry.call(
                model=chosen, instructions=SUBAGENT, history=history, tools=SCHEMAS, effort=effort(chosen)
            )
            spent += usage.record(reply, conversation=False, model=chosen)
            history += reply.output
            text = reply.text or text
            calls = [item for item in reply.output if item["type"] == "function_call"]
            if not calls:
                break
            history += await asyncio.gather(*(runner.run(call, FUNCTIONS, show=False) for call in calls))
        else:
            text = f"(stopped after {MAX_ROUNDS} rounds)\n{text}"
    note(f"  agent finished: {chosen}, {rounds} rounds, ${spent:.2f}")
    return text or "(the subagent gave no answer)"


def pick(model: str) -> str:
    """The model for a subagent: the current one, or the provider's smartest or cheapest current model."""
    current = config.get("model")
    name, _ = registry.split(current)
    find = {"smart": listing.smartest, "fast": listing.cheapest}.get(model)
    found = find(name) if find else None
    return f"{name}/{found}" if found else current


def effort(model: str) -> str | None:
    """The user's reasoning level if the model offers it. Otherwise None: the provider's default."""
    level = config.get("effort")
    return level if level in listing.efforts(model) else None
