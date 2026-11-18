import asyncio
import atexit
import json
import shutil
import tempfile
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

from zero_harness import config, safety
from zero_harness.ui import notes, user_input
from zero_harness.ui.notes import note

PROTECTED = [".env", ".env.*", ".git", ".ssh", ".aws", ".gnupg", ".netrc", ".npmrc", ".pypirc", "*.pem", "*.key"]
APPROVALS = config.HOME / "approvals.jsonl"
SCRATCH = Path(tempfile.mkdtemp(prefix="zero-scratch-")).resolve()
atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)


async def ask(**request) -> str | None:
    """Ask the user and log the answer with `request`, to tune what auto mode allows.

    Return None if allowed, else the result for the model, with any text the user typed.
    """
    reply = (await user_input.ask("allow? [y/N]")).strip()
    allowed = reply.lower() in ("y", "yes")
    entry = {"time": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "cwd": str(Path.cwd()), **request, "allowed": allowed}
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
    """auto allows edits inside the working directory or scratch folder, except secrets and git internals.

    auto-max allows every edit.
    """
    mode = config.get("mode")
    if mode == "auto-max":
        note("  ↳ auto-approved: auto-max")
        return None
    if mode == "ask":
        return await ask(edit=path, reason="ask mode")
    if reason := edit_risk(path):
        note(f"  ↳ asking: {reason}", style=notes.CAUTION)
        return await ask(edit=path, reason=reason)
    note("  ↳ auto-approved")
    return None


def edit_risk(path: str) -> str | None:
    """Why an edit to `path` needs the user, or None if auto mode may allow it."""
    target, root = Path(path).resolve(), Path.cwd().resolve()
    if target.is_relative_to(SCRATCH):
        return None
    if not target.is_relative_to(root):
        return "outside the project"
    parts = target.relative_to(root).parts
    if any(fnmatch(part, pattern) for part in parts for pattern in PROTECTED):
        return "protected file"
    return None


async def approve_command(command: str, purpose: str) -> str | None:
    """auto runs commands the reviewer rates clear. auto-max runs all but known destructive commands."""
    mode, reason = config.get("mode"), "ask mode"
    if mode == "auto-max":
        if not (match := safety.DESTRUCTIVE.search(command)):
            note("  ↳ auto-approved: auto-max")
            return None
        reason = f"destructive: {match.group().strip()}"
        note(f"  ↳ asking: {reason}", style=notes.CAUTION)
    elif mode == "auto":
        run, reason = await asyncio.to_thread(safety.review, command, SCRATCH)
        if run:
            note(f"  ↳ auto-approved: {reason}")
            return None
        note(f"  ↳ asking: {reason}", style=notes.CAUTION)
    if purpose:
        note(f"  ↳ {purpose}", style=notes.CAUTION)
    return await ask(command=command, purpose=purpose, reason=reason)
