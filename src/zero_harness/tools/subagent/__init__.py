import asyncio
import json
from pathlib import Path

from zero_harness import context, permissions, prompt, usage, workdir
from zero_harness.models import registry
from zero_harness.tools import bash, edit_file, grep, read_file, runner, web_fetch, web_search
from zero_harness.tools.subagent import models, worktrees
from zero_harness.tools.subagent.log import Log
from zero_harness.ui import notes, user_input
from zero_harness.ui.notes import note

# No subagent tool for subagents: they can't start their own.
READ_ONLY = [read_file, grep, web_search, web_fetch]
EDITING = [*READ_ONLY, edit_file, bash]
MAX_ROUNDS = 30
running = asyncio.Semaphore(4)  # at most this many subagents at once
started = 0  # numbers subagents, for their labels
tasks: dict[str, asyncio.Task] = {}  # running subagents by label
logs: dict[str, Path] = {}  # every subagent's live log this session, for /watch

SCHEMA = {
    "type": "function",
    "name": "subagent",
    "description": (
        "Start a subagent in the background. Its final answer arrives later as a message; the conversation goes on "
        "meanwhile. It can't see this conversation, so give it everything: the goal, relevant paths and facts, and "
        "what to return. Start several to work in parallel. By default it is read-only (grep, read_file, "
        "web_search, web_fetch). With edit=true it also gets edit_file and bash in its own copy of the project, and "
        "its changes merge into the user's files when it finishes; give parallel editing subagents separate files "
        "to avoid conflicts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "A self-contained brief: goal, context, and what to return."},
            "model": {
                "type": "string",
                "description": (
                    "fast (default when read-only), smart (the user confirms each one), current (your model; default "
                    "with edit=true), or an exact provider/model-id (the user confirms it). Editing can't use fast."
                ),
            },
            "edit": {
                "type": "boolean",
                "description": "Let it edit files and run commands in its own copy. Default false.",
            },
        },
        "required": ["task"],
    },
}


def on_finish(report: str) -> None:
    """Called with a subagent's report when it finishes. main replaces it to queue the report like a message."""


async def run(task: str, model: str = "", edit: bool = False) -> str:
    """Start a subagent in the background and return at once, so the conversation goes on while it works."""
    if edit and model == "fast":
        return "error: editing subagents can't use fast. Leave model out (current), or use smart."
    model = model or ("current" if edit else "fast")
    top = await asyncio.to_thread(worktrees.repo, Path.cwd()) if edit else None
    if edit and top is None:
        return "error: editing subagents need a git repo. Use a read-only subagent, or make the edits yourself."
    chosen, level = await models.pick(model)
    if model == "smart" and (denied := await allow_smart(chosen, level, task)):
        return f"error: {denied}. Continue yourself, or ask the user."
    global started
    started += 1
    label = f"subagent {started}"
    tasks[label] = asyncio.create_task(background(label, chosen, level, task, top))
    return (
        f"started {label} on {' '.join(filter(None, (chosen, level)))}. Its report arrives as a message starting "
        f"with [{label}] when it finishes. Meanwhile keep working on other things, or end your turn. Don't wait or "
        "check on it."
    )


async def background(label: str, model: str, level: str | None, task: str, top: Path | None) -> None:
    """Run a subagent, show it as working below the conversation, and report when done. Cancelling reports nothing."""
    shown = " ".join(filter(None, (model, level)))
    detail = f"/watch {label.split()[-1]}  {shown}  {' '.join(task.split())}"
    user_input.subagents[label] = ("waiting", detail)
    logs[label] = permissions.SCRATCH / f"{label.replace(' ', '-')}.log"
    log = Log(logs[label], f"{label}  {shown}{'  (editing)' if top else ''}\n{task}")
    ending = "stopped"
    try:
        async with running:
            user_input.subagents[label] = ("working", detail)
            if top:
                report = await edit_in_worktree(label, model, level, task, top, log)
            else:
                instructions = prompt.subagent(workdir.root(), edit=False)
                report = await work(model, level, task, instructions, READ_ONLY, label, log)
        ending = "finished"
    except Exception as error:  # noqa: BLE001 - a failed subagent reports its error instead of vanishing
        report = f"error: {type(error).__name__}: {error}"
        ending = f"failed: {report}"
    finally:
        user_input.subagents.pop(label, None)
        tasks.pop(label, None)
        log.close(f"{label} {ending}")
    on_finish(f"[{label} finished] Its task: {task}\n\nIts report:\n{report}")


async def edit_in_worktree(label: str, model: str, level: str | None, task: str, top: Path, log: Log) -> str:
    base = await asyncio.to_thread(worktrees.snapshot, top)
    tree = await asyncio.to_thread(worktrees.create, top, base, label)
    try:
        token = workdir.tree.set(tree)
        try:
            answer = await work(model, level, task, prompt.subagent(tree.root, edit=True), EDITING, label, log)
        finally:
            workdir.tree.reset(token)
        merged = await merge_back(tree, base)
        log.write(merged)
        return answer + merged
    finally:
        await asyncio.to_thread(worktrees.remove, tree)


def cancel_all() -> int:
    """Stop every running subagent. Returns how many there were."""
    for task in tasks.values():
        task.cancel()
    return len(tasks)


async def work(model: str, level: str | None, task: str, instructions: str, tools: list, label: str, log: Log) -> str:
    """Run the subagent's tool loop, shown only in its log, and return its final answer."""
    schemas = [tool.SCHEMA for tool in tools]
    functions = {tool.SCHEMA["name"]: tool.run for tool in tools}
    history = [{"role": "user", "content": task}]
    spent, text = 0.0, ""
    for rounds in range(1, MAX_ROUNDS + 1):
        reply = await registry.call(
            model=model, instructions=instructions, history=history, tools=schemas, effort=level, live=log
        )
        spent += usage.record(reply, conversation=False, model=model)
        history += reply.output
        text = reply.text or text
        calls = [item for item in reply.output if item["type"] == "function_call"]
        if not calls:
            break
        if edit_file not in tools:
            outputs = await asyncio.gather(*(runner.run(call, functions, show=False) for call in calls))
        else:  # edits and commands one at a time, like the main agent's
            outputs = [await runner.run(call, functions, show=False) for call in calls]
        for call, output in zip(calls, outputs):
            log.tool(call["name"], json.loads(call["arguments"]), output["output"])
        history += outputs
        if (used := reply.usage.input_tokens) > context.TRIM_AT_TOKENS:
            context.trim(history, f"{label}'s last call used {used:,} input tokens (limit {context.TRIM_AT_TOKENS:,})")
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


async def allow_smart(model: str, level: str | None, task: str) -> str | None:
    """Ask before each smart subagent: it runs the user's most expensive model. None if allowed."""
    async with permissions.asking:
        note(f"start a smart subagent on {' '.join(filter(None, (model, level)))}:", style=notes.CAUTION)
        note(f"  ↳ {' '.join(task.split())[:300]}", style=notes.CAUTION)
        return await permissions.ask(smart_subagent=model, task=task)
