import asyncio
import shlex
import subprocess
import sys

import questionary

from zero_harness.tools import agent
from zero_harness.ui.notes import note

DESCRIPTION = "follow a subagent live"
ANYTIME = True


def complete(words: list[str]) -> list[str]:
    return [] if words else [label.split()[-1] for label in agent.logs]


async def run(history: list, args: str) -> None:
    """/watch opens a window that follows a subagent's log. /watch 2 picks agent 2; with several, a menu asks."""
    if not agent.logs:
        note("no subagents yet")
        return
    label = f"agent {args}" if args else None
    if label is None:
        running = [label for label in agent.logs if label in agent.tasks]
        choices = running or list(agent.logs)
        label = choices[0] if len(choices) == 1 else await questionary.select("subagent:", choices=choices).ask_async()
    if label not in agent.logs:
        note(f"no {label}. Subagents this session: {', '.join(agent.logs)}")
        return
    log = agent.logs[label]
    follow = f"tail -n +1 -f {shlex.quote(str(log))}"
    if sys.platform == "darwin":
        # A .command file opens in the user's default terminal app as a new window.
        script = log.with_suffix(".command")
        script.write_text(f"#!/bin/sh\nclear\nprintf '\\033]0;zero {label}\\007'\n{follow}\n")
        script.chmod(0o755)
        await asyncio.to_thread(subprocess.run, ["open", str(script)], check=False)
        note(f"opened {label} in a new window")
    else:
        note(f"follow {label} in another terminal: {follow}")
