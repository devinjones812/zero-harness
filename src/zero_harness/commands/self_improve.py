import shlex
import shutil
import subprocess
import sys
from datetime import datetime

from zero_harness import config, sessions
from zero_harness.prompt import REPO
from zero_harness.ui import notes
from zero_harness.ui.notes import note

DESCRIPTION = "fix zero itself"
# Runs even while the agent works. It only reads the session and opens a window, so the turn continues.
ANYTIME = True

BRIEF = """# Self-improve

The user typed /self-improve in another zero session. Find where zero, the harness, fell short in that session,
and fix it.

User's note: {note}

Files:
- {folder}/screen.txt: recorded terminal output since the previous self-improve capture, or since the session
  started if this is the first. Start here.
- {folder}/session.json: current model history for the whole session, including messages, tool calls, and tool results.
  Read parts of it only when screen.txt is not enough, e.g. to see a full command or what the model received.

You are in zero's repo. Investigate the code to find the cause of each issue. If it helps, you can search the
web, e.g. for how other harnesses handle the same problem.

Steps:
1. Propose fixes. For each issue: what went wrong, the cause, and the fix. Wait for the user's approval or comments.
2. Make the approved fixes. Check that zero imports.
3. Tell the user to type /reload in the other session to apply them.

{earlier}Rules:
- Prefer code fixes. Change the prompt only when needed, and keep it short.
- Keep the code clean: the smallest change that fixes the cause. No new layers or abstractions.
- Ask the user only when absolutely needed.
- Don't commit. Commit {checkpoint} holds the code from before your changes. To roll back:
  git reset --hard {checkpoint}
"""

EARLIER = """Earlier self-improve captures in this session:
{runs}
Focus on output since the last capture. Use earlier folders only for context; a capture does not mean its issues
were fixed. `git diff {last} {checkpoint}` shows what changed since the last capture.

"""


async def run(history: list, args: str) -> None:
    if not (REPO / ".git").exists():
        note("self-improve needs zero to run from a git clone. Clone the repo and run `uv tool install --editable .`")
        return
    if not history:
        note("nothing to improve yet: this session is empty")
        return
    checkpoint = commit()
    if checkpoint is None:
        return
    folder = config.HOME / "self-improve" / f"{datetime.now():{sessions.STAMP}}"
    folder.mkdir(parents=True)
    screen = sessions.screen().splitlines()
    (folder / "screen.txt").write_text("".join(f"{line.rstrip()}\n" for line in screen))
    earlier = ""
    if sessions.improved:
        runs = "\n".join(f"- checkpoint {run['checkpoint']}, files in {run['folder']}" for run in sessions.improved)
        earlier = EARLIER.format(runs=runs, last=sessions.improved[-1]["checkpoint"], checkpoint=checkpoint)
    sessions.improved.append({"at": len(history), "folder": str(folder), "checkpoint": checkpoint})
    marker(checkpoint)
    sessions.clear_screen()
    sessions.save(history)
    shutil.copy(sessions.current, folder / "session.json")
    brief = BRIEF.format(note=args or "(none)", folder=folder, checkpoint=checkpoint, earlier=earlier)
    (folder / "brief.md").write_text(brief)
    message = f"Read {folder / 'brief.md'} and follow it."
    open_window(f"cd {shlex.quote(str(REPO))} && zero {shlex.quote(message)}")
    note(f"checkpoint {checkpoint}. Type /reload here after the fixes are in.")


def marker(checkpoint: str) -> None:
    notes.console.rule(f"self-improve ran here (checkpoint {checkpoint})", style="dim")


def commit() -> str | None:
    """Commit zero's repo as it is now. Return the commit hash, or None if the commit failed."""

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(REPO), *args], check=False, capture_output=True, text=True)

    git("add", "-A")
    git("commit", "-m", "checkpoint before self-improve")
    if left := git("status", "--porcelain").stdout.strip():
        note(f"could not commit zero's repo, so there is no checkpoint to roll back to:\n{left}", style="red")
        return None
    return git("rev-parse", "--short", "HEAD").stdout.strip()


def open_window(command: str) -> None:
    """Run `command` in a new macOS Terminal window. Elsewhere, print it for the user to run."""
    if sys.platform == "darwin":
        script = [
            "on run argv",
            'tell application "Terminal"',
            "do script (item 1 of argv)",
            "activate",
            "end tell",
            "end run",
        ]
        lines = [arg for line in script for arg in ("-e", line)]
        if subprocess.run(["osascript", *lines, command], check=False, capture_output=True).returncode == 0:
            return
    note(f"open a new terminal and run:\n{command}")
