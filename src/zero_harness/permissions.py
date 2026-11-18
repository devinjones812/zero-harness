import asyncio
import atexit
import shutil
import tempfile
from fnmatch import fnmatch
from pathlib import Path

from zero_harness import config, safety
from zero_harness.ui import user_input
from zero_harness.ui.notes import note

PROTECTED = [".env", ".env.*", ".git", ".ssh", ".aws", ".gnupg", ".netrc", ".npmrc", ".pypirc", "*.pem", "*.key"]
SCRATCH = Path(tempfile.mkdtemp(prefix="zero-scratch-")).resolve()
atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)


async def ask() -> str | None:
    """Ask the user. Return None if allowed, else the result for the model, with any text the user typed."""
    reply = (await user_input.ask("allow? [y/N]")).strip()
    if reply.lower() in ("y", "yes"):
        return None
    if reply.lower() in ("", "n", "no"):
        return "user denied this"
    return f"user denied this and said: {reply}"


async def approve_edit(path: str) -> str | None:
    """In auto mode, allow edits inside the working directory or scratch folder, except secrets and git internals."""
    if not config.get("auto"):
        return await ask()
    if reason := edit_risk(path):
        note(f"  ↳ asking: {reason}")
        return await ask()
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
    """In auto mode, run commands Jev rates clear without asking. Everything else asks."""
    if config.get("auto"):
        run, reason = await asyncio.to_thread(safety.review, command, SCRATCH)
        note(f"  ↳ {'auto-approved' if run else 'asking'}: {reason}")
        if run:
            return None
    if purpose:
        note(f"  ↳ {purpose}")
    return await ask()
