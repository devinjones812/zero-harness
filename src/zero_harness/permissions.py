"""Approval for the agent's edits and commands, by mode. ask: always ask. auto-review: allow edits inside the project
or scratch folder except protected files (PROTECTED), and commands the reviewer in safety.py clears. auto-max: allow
all but destructive commands. Each answer is logged to approvals.jsonl, to tune what auto modes allow."""

import asyncio
import atexit
import json
import shutil
import tempfile
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

from zero_harness import config, safety, workdir
from zero_harness.ui import notes, user_input
from zero_harness.ui.notes import note

PROTECTED = [".env", ".env.*", ".git", ".ssh", ".aws", ".gnupg", ".netrc", ".npmrc", ".pypirc", "*.pem", "*.key"]
APPROVALS = config.HOME / "approvals.jsonl"
SCRATCH = Path(tempfile.mkdtemp(prefix="zero-scratch-")).resolve()
atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
# Subagents run alongside the main agent; their questions take turns so each reads as one block.
asking = asyncio.Lock()


def tell(text: str, style: str = "dim") -> None:
    """A note, labeled with the subagent it comes from."""
    current = workdir.tree.get()
    note(f"  [{current.label}] {text.strip()}" if current else text, style=style)


def allowed(reason: str) -> None:
    """Note an auto-approval. Subagents work quietly, so only the main agent's show."""
    if not workdir.tree.get():
        note(f"  ↳ auto-approved{reason}")


async def ask(**request) -> str | None:
    """Ask the user and log the answer with `request`, to tune what auto mode allows.

    Return None if allowed, else the result for the model, with any text the user typed.
    """
    reply = (await user_input.ask("allow? [y/N]")).strip()
    allowed = reply.lower() in ("y", "yes")
    entry = {"time": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "cwd": str(workdir.root()), **request, "allowed": allowed}
    if not allowed and reply:
        entry["reply"] = reply
    with APPROVALS.open("a") as log:
        log.write(json.dumps(entry) + "\n")
    if allowed:
        return None
    if reply.lower() in ("", "n", "no"):
        return "user denied this"
    return f"user denied this and said: {reply}"


async def approve_edit(path: str) -> str | None:
    """Apply the approval mode to one edit. A subagent's edits inside its own worktree need no approval: they reach
    the user's files only through approve_changes."""
    current = workdir.tree.get()
    if current and not edit_risk(path, current.top):
        return None
    mode = config.get("mode")
    if mode == "auto-max":
        allowed(": auto-max")
        return None
    reason = "ask mode" if mode == "ask" else edit_risk(path)
    if reason is None:
        allowed("")
        return None
    async with asking:
        if current:
            tell(f"edit {path}", style=notes.CAUTION)
        if mode != "ask":
            tell(f"  ↳ asking: {reason}", style=notes.CAUTION)
        return await ask(edit=path, reason=reason)


async def approve_changes(label: str, paths: list[str]) -> str | None:
    """One approval to apply a subagent's changes to the user's files, with the same rules as single edits."""
    mode = config.get("mode")
    if mode == "auto-max":
        note("  ↳ auto-approved: auto-max")
        return None
    risks = [risk for path in paths if (risk := edit_risk(path))]
    if mode == "auto-review" and not risks:
        note("  ↳ auto-approved")
        return None
    reason = risks[0] if risks else "ask mode"
    async with asking:
        note(f"  [{label}] apply its changes to: {', '.join(paths)}", style=notes.CAUTION)
        if mode != "ask":
            note(f"  ↳ asking: {reason}", style=notes.CAUTION)
        return await ask(edit=", ".join(paths), reason=reason)


def edit_risk(path: str, root: Path | None = None) -> str | None:
    """Why an edit to `path` needs the user, or None if auto-review may allow it. `root` defaults to the working
    directory."""
    target, root = workdir.resolve(path).resolve(), (root or workdir.root()).resolve()
    if target.is_relative_to(SCRATCH) and not workdir.tree.get():
        return None
    if not target.is_relative_to(root):
        return "outside the project"
    parts = target.relative_to(root).parts
    if any(fnmatch(part, pattern) for part in parts for pattern in PROTECTED):
        return "protected file"
    return None


async def approve_command(command: str, purpose: str) -> str | None:
    """Apply the approval mode; only auto-review consults the reviewer.

    Return None to allow execution, or the user's denial for the model.
    """
    mode, reason = config.get("mode"), "ask mode"
    if mode == "auto-max":
        if not (match := safety.DESTRUCTIVE.search(command)):
            allowed(": auto-max")
            return None
        reason = f"destructive: {match.group().strip()}"
    elif mode == "auto-review":
        run, reason = await asyncio.to_thread(safety.review, command, SCRATCH, workdir.root())
        if run:
            allowed(f": {reason}")
            return None
    async with asking:
        if workdir.tree.get():
            tell(f"run {command}", style=notes.CAUTION)
        if mode != "ask":
            tell(f"  ↳ asking: {reason}", style=notes.CAUTION)
        if purpose:
            tell(f"  ↳ {purpose}", style=notes.CAUTION)
        return await ask(command=command, purpose=purpose, reason=reason)
