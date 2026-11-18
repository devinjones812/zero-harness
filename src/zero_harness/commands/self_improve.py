import shlex
import shutil
import subprocess
import sys
from datetime import datetime

from zero_harness import config, sessions
from zero_harness.prompt import REPO
from zero_harness.ui import notes
from zero_harness.ui.notes import note

DESCRIPTION = "Open a new zero in its own repo to find and fix what went wrong here. Add a note: /self-improve <note>."

BRIEF = """# Self-improve

The user typed /self-improve in another zero session. Find where zero, the harness, fell short in that session,
and fix it.

User's note: {note}

Files:
- {folder}/screen.txt: everything the user saw in the terminal. Most issues show up here, from the user's view.
  It probably has what you need. Start here.
- {folder}/session.json: the session as the model saw it: messages, full tool calls, and tool results. It is large.
  Read parts of it only when screen.txt is not enough, e.g. to see a full command or what the model received.

You are in zero's repo. Investigate the code to find the cause of each issue. If it helps, you can search the
web, e.g. for how other harnesses handle the same problem.

Steps:
1. Propose fixes. For each issue: what went wrong, the cause, and the fix. Wait for the user's approval or comments.
2. Make the approved fixes. Check that zero imports.
3. Tell the user to type /reload in the other session to apply them.

Rules:
- Prefer code fixes. Change the prompt only when needed, and keep it short.
- Keep the code clean: the smallest change that fixes the cause. No new layers or abstractions.
- Ask the user only when absolutely needed.
- Don't commit. Commit {checkpoint} holds the code from before your changes. To roll back:
  git reset --hard {checkpoint}
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
    screen = notes.console.export_text(clear=False).splitlines()
    (folder / "screen.txt").write_text("\n".join(line.rstrip() for line in screen) + "\n")
    shutil.copy(sessions.current, folder / "session.json")
    (folder / "brief.md").write_text(BRIEF.format(note=args or "(none)", folder=folder, checkpoint=checkpoint))
    message = f"Read {folder / 'brief.md'} and follow it."
    open_window(f"cd {shlex.quote(str(REPO))} && zero {shlex.quote(message)}")
    note(f"checkpoint {checkpoint}. Type /reload here after the fixes are in.")


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
        script = ["on run argv", 'tell application "Terminal"', "do script (item 1 of argv)", "activate", "end tell", "end run"]
        lines = [arg for line in script for arg in ("-e", line)]
        if subprocess.run(["osascript", *lines, command], check=False, capture_output=True).returncode == 0:
            return
    note(f"open a new terminal and run:\n{command}")
