import asyncio
from fnmatch import fnmatch
from pathlib import Path

from zero_harness import config, safety
from zero_harness.ui import user_input
from zero_harness.ui.notes import note

PROTECTED = [".env", ".env.*", ".git", ".ssh", ".aws", ".gnupg", ".netrc", ".npmrc", ".pypirc", "*.pem", "*.key"]


async def ask() -> bool:
    return (await user_input.ask("allow? [y/N]")).strip().lower() == "y"


async def approve_edit(path: str) -> bool:
    """In auto mode, allow edits inside the working directory, except secrets and git internals."""
    if config.get("auto") and in_project(path):
        note("  ↳ auto-approved")
        return True
    return await ask()


def in_project(path: str) -> bool:
    """True if `path` is inside the working directory and no part of it matches PROTECTED."""
    target, root = Path(path).resolve(), Path.cwd().resolve()
    if not target.is_relative_to(root):
        return False
    parts = target.relative_to(root).parts
    return not any(fnmatch(part, pattern) for part in parts for pattern in PROTECTED)


async def approve_command(command: str) -> bool:
    """In auto mode, run commands Jev rates clear without asking. Everything else asks."""
    if not config.get("auto"):
        return await ask()
    run, reason = await asyncio.to_thread(safety.review, command)
    note(f"  ↳ {'auto-approved' if run else 'asking'}: {reason}")
    return run or await ask()
