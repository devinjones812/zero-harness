import asyncio

from prompt_toolkit.application import in_terminal

from zero_harness import config, errors, usage
from zero_harness.commands import model as model_command
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
choosing = asyncio.Lock()
TIERS = {"smart": ("hard, narrow problems", listing.smartest), "fast": ("simple searches", listing.cheapest)}

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
                "description": (
                    "current (default): your model. smart: the user's model for narrow, hard problems. fast: the "
                    "user's cheap model for simple searches. Or an exact provider/model the user names, such as "
                    "openai/gpt-6.2-astra."
                ),
            },
        },
        "required": ["task"],
    },
}


async def run(task: str, model: str = "current") -> str:
    chosen = await pick(model)
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


async def pick(model: str) -> str:
    """The model for a subagent: the current one, the user's smart or fast model, or an exact provider/model."""
    if model in ("", "current"):
        return config.get("model")
    if model not in TIERS:
        return await exact(model)
    async with choosing:  # parallel subagents ask the user once
        if not config.get(f"{model}_model"):
            picked = await ask_tier(model)
            if not picked:
                note(f"no {model} model picked; this subagent uses your current model.")
                return config.get("model")
            config.update(f"{model}_model", picked)
            note(f"saved {model} subagent model: {picked}. Ask zero to change it.")
            return picked
    return config.get(f"{model}_model")


async def exact(model: str) -> str:
    """Check that a provider/model exists and the key can use it. Raises ValueError with what to do instead."""
    name, model_id = registry.split(model)
    if not registry.has_key(name):
        raise ValueError(f"no API key for {name}. Use a provider with a key, or ask the user to add one with /model.")
    await load_account(name)
    if name in registry.account and model_id not in registry.account[name]:
        raise ValueError(f"{name} has no model {model_id!r} for this key. Options: {', '.join(listing.latest(name))}")
    return f"{name}/{model_id}"


async def suggest(tier: str) -> str | None:
    """The current provider's smartest or cheapest model, or else the first other provider with a key that has one."""
    current, _ = registry.split(config.get("model"))
    for name in [current, *registry.providers()]:
        if registry.has_key(name):
            await load_account(name)
            if found := TIERS[tier][1](name):
                return f"{name}/{found}"
    return None


async def load_account(name: str) -> None:
    """Learn which models the key can use, once. zero loads only the current provider's at startup."""
    if name not in registry.account:
        try:
            await registry.load_account(name)
        except errors.recoverable():
            pass


async def ask_tier(tier: str) -> str | None:
    """Have the user pick the model for a tier, starting on a suggestion. None if they cancel."""
    use, _ = TIERS[tier]
    suggested = await suggest(tier)
    note(f'zero wants a "{tier}" subagent, for {use}. Pick the model to use for {tier} subagents; zero saves it.')
    if suggested:
        note(
            f"Preselected: {suggested}, your provider's {'priciest' if tier == 'smart' else 'cheapest'} current model."
        )
    async with in_terminal():  # pauses zero's input box so the picker can use the terminal
        return await model_command.pick_configured(suggested)


def effort(model: str) -> str | None:
    """The user's reasoning level if the model offers it. Otherwise None: the provider's default."""
    level = config.get("effort")
    return level if level in listing.efforts(model) else None
