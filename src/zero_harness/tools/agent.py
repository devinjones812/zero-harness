import asyncio
from pathlib import Path

from prompt_toolkit.application import in_terminal

from zero_harness import config, errors, permissions, prompt, usage, workdir, worktrees
from zero_harness.commands import model as model_command
from zero_harness.models import listing, registry
from zero_harness.tools import bash, edit_file, grep, read_file, runner, web_fetch, web_search
from zero_harness.ui.notes import note

# No agent tool for subagents: they can't start their own.
READ_ONLY = [read_file, grep, web_search, web_fetch]
EDITING = [*READ_ONLY, edit_file, bash]
MAX_ROUNDS = 30
running = asyncio.Semaphore(4)  # at most this many subagents at once
choosing = asyncio.Lock()
TIERS = {"smart": ("hard, narrow problems", listing.smartest), "fast": ("simple searches", listing.cheapest)}
started = 0  # numbers editing subagents, for their labels

SCHEMA = {
    "type": "function",
    "name": "agent",
    "description": (
        "Hand a task to a subagent. It returns only its final answer. It can't see this conversation, so give it "
        "everything: the goal, relevant paths and facts, and what to return. Call agent several times in one reply "
        "to run subagents in parallel. By default it is read-only (grep, read_file, web_search, web_fetch). With "
        "edit=true it also gets edit_file and bash in its own copy of the project, and its changes merge into the "
        "user's files when it finishes; give parallel editing subagents separate files to avoid conflicts."
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
            "edit": {"type": "boolean", "description": "Let it edit files and run commands. Default false."},
        },
        "required": ["task"],
    },
}


async def run(task: str, model: str = "current", edit: bool = False) -> str:
    chosen = await pick(model)
    async with running:
        if not edit:
            return await work(chosen, task, prompt.subagent(workdir.root(), edit=False), READ_ONLY, "agent")
        top = await asyncio.to_thread(worktrees.repo, Path.cwd())
        if top is None:
            return "error: editing subagents need a git repo. Use a read-only subagent, or make the edits yourself."
        global started
        started += 1
        base = await asyncio.to_thread(worktrees.snapshot, top)
        tree = await asyncio.to_thread(worktrees.create, top, base, f"agent {started}")
        try:
            token = workdir.tree.set(tree)
            try:
                answer = await work(chosen, task, prompt.subagent(tree.root, edit=True), EDITING, tree.label)
            finally:
                workdir.tree.reset(token)
            return answer + await merge_back(tree, base)
        finally:
            await asyncio.to_thread(worktrees.remove, tree)


async def work(model: str, task: str, instructions: str, tools: list, label: str) -> str:
    """Run the subagent's tool loop quietly and return its final answer."""
    schemas = [tool.SCHEMA for tool in tools]
    functions = {tool.SCHEMA["name"]: tool.run for tool in tools}
    history = [{"role": "user", "content": task}]
    spent, text = 0.0, ""
    for rounds in range(1, MAX_ROUNDS + 1):
        reply = await registry.call(
            model=model, instructions=instructions, history=history, tools=schemas, effort=effort(model)
        )
        spent += usage.record(reply, conversation=False, model=model)
        history += reply.output
        text = reply.text or text
        calls = [item for item in reply.output if item["type"] == "function_call"]
        if not calls:
            break
        if tools is READ_ONLY:
            history += await asyncio.gather(*(runner.run(call, functions, show=False) for call in calls))
        else:  # edits and commands one at a time, like the main agent's
            history += [await runner.run(call, functions, show=False) for call in calls]
    else:
        text = f"(stopped after {MAX_ROUNDS} rounds)\n{text}"
    note(f"  {label} finished: {model}, {rounds} rounds, ${spent:.2f}")
    return text or "(the subagent gave no answer)"


async def merge_back(tree: workdir.Tree, base: str) -> str:
    """Merge the subagent's changes into the user's files, after one approval. Tell the main agent what happened."""
    writes, conflicts = await asyncio.to_thread(worktrees.plan, tree, base)
    if not writes and not conflicts:
        return "\n\n(it changed no files)"
    report = ""
    if writes:
        paths = list(writes)
        if denied := await permissions.approve_changes(tree.label, [str(tree.repo / path) for path in paths]):
            return f"\n\nIts changes were not applied: {denied}. Its diff:\n{worktrees.diff(tree, base, paths)}"
        await asyncio.to_thread(worktrees.apply, tree.repo, writes)
        note(f"  [{tree.label}] applied changes to {', '.join(paths)}")
        report += f"\n\nzero applied its changes to: {', '.join(paths)}"
    if conflicts:
        note(f"  [{tree.label}] not applied, changed elsewhere too: {', '.join(conflicts)}", style="yellow")
        report += (
            f"\n\nNot applied, because these files also changed since it started: {', '.join(conflicts)}. "
            f"Apply what still fits yourself. Its diff:\n{worktrees.diff(tree, base, conflicts)}"
        )
    return report


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
            f"Preselected: {suggested}, your provider's {'most expensive' if tier == 'smart' else 'cheapest'} current model."
        )
    async with in_terminal():  # pauses zero's input box so the picker can use the terminal
        return await model_command.pick_configured(suggested)


def effort(model: str) -> str | None:
    """The user's reasoning level if the model offers it. Otherwise None: the provider's default."""
    level = config.get("effort")
    return level if level in listing.efforts(model) else None
