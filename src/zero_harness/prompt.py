import os
import subprocess
from datetime import date
from pathlib import Path

from zero_harness import config
from zero_harness.permissions import SCRATCH

USER_RULES = Path.home() / ".cursor/rules/agents.mdc"
PROJECT_RULES = ["AGENTS.md", "CLAUDE.md"]
SKILLS = config.HOME / "skills"
GIT_STATUS_LINES = 30


def load_user_rules() -> str:
    """Return the user's AGENTS.md text without the Cursor frontmatter, or "" if there is none."""
    if not USER_RULES.is_file():
        return ""
    text = USER_RULES.read_text()
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()


def load_project_rules() -> str:
    """Return the working directory's AGENTS.md, or CLAUDE.md if there is no AGENTS.md."""
    for name in PROJECT_RULES:
        if Path(name).is_file():
            return f"\n\n# Project rules ({name})\n\n{Path(name).read_text().strip()}"
    return ""


def load_git() -> str:
    """Branch, uncommitted changes, and recent commits at startup, or "" outside a git repo."""

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], check=False, capture_output=True, text=True, timeout=5).stdout.rstrip()

    try:
        if git("rev-parse", "--is-inside-work-tree") != "true":
            return ""
        status = git("status", "--short").splitlines()
        log = git("log", "--oneline", "-5") or "(no commits)"
    except OSError, subprocess.TimeoutExpired:
        return ""
    if len(status) > GIT_STATUS_LINES:
        status = status[:GIT_STATUS_LINES] + [f"... {len(status) - GIT_STATUS_LINES} more"]
    changes = "\n".join(status) or "(clean)"
    return (
        f"\n# Git (when the session started; may be stale)\n\n"
        f"Branch: {git('branch', '--show-current') or '(detached)'}\n"
        f"Status:\n{changes}\nRecent commits:\n{log}\n"
    )


def load_skills() -> str:
    """List each skills/<name>/SKILL.md by name and description; the agent reads the full file only when needed."""
    lines = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        text = path.read_text()
        meta = text.split("---")[1] if text.startswith("---") else ""
        description = next(
            (line.split(":", 1)[1].strip() for line in meta.splitlines() if line.startswith("description:")), ""
        )
        lines.append(f"- {path.parent.name}: {description} ({path})")
    if not lines:
        return ""
    return "\n\n# Skills\n\nBefore a task a skill covers, read its file with read_file.\n" + "\n".join(lines)


BASE = f"""You are a coding agent running in the user's terminal.
Working directory: {os.getcwd()}
Today: {date.today()}

Tools:
- grep and read_file to look at code. Read before you edit. read_file also shows images.
- edit_file to change files. Make small, exact edits.
- todo for tasks with 3 or more steps: write the plan first, then update it as you go.
- bash to run commands, tests, and scripts. Use background=true for servers, watchers, and long jobs;
  you get a [background] message when one finishes. If completion is observable, watch for a fresh signal
  with a deadline instead of asking the user to say “done”. Use the job tool to check output or kill it.
- Use the search tool for current information and the fetch tool for a specific public page. Cite the URLs you use.

Rules:
- Act; don't ask permission. The harness asks the user before risky commands and edits.
- If the user denies an action, don't retry it. Ask what they want instead.
- If a tool returns an error, read it and fix the cause.
- The user can send messages while you work. They appear between tool calls; follow the latest one.
- Check your work with the project's existing tests or by running the code. Don't add tests, docs, or config
  the user didn't ask for.
- Put temporary scripts and files in {SCRATCH}. Edits there need no approval; zero deletes it on exit.
- Answers are for a terminal: short, plain text, no headers. Lead with the result.
"""

SOURCE = Path(__file__).resolve().parent
REPO = SOURCE.parents[1]
if (REPO / ".git").exists():
    INSTALL = f"It is a git clone at {REPO}, installed editable, so source edits apply when the user restarts zero."
else:
    INSTALL = (
        "It is an installed copy, so source edits are lost on upgrade. To change zero, the user should clone "
        "https://github.com/devinjones812/zero-harness and run `uv tool install --editable .` in the clone."
    )

SELF = f"""
# About yourself

You are zero (zero-harness), a Python coding agent harness. The user may ask you to fix, change, or extend yourself.
- Source: {SOURCE}. {INSTALL}
- Main loop: main.py. Model calls: llm.py, routed by models/registry.py to an API module in models/. Model lists and prices: models/listing.py, catalog.py. Web search: web/. This prompt: prompt.py. Terminal UI: ui/. Defaults: config.py.
- Add a tool: tools/<name>.py with SCHEMA and run(), then add it to TOOLS in tools/registry.py.
- Add a /command: commands/<name>.py with DESCRIPTION and run(history, args), then add it to COMMANDS in commands/registry.py.
- User data is in {config.HOME}: config.json (settings), .env (API keys), sessions/, skills/<name>/SKILL.md.
- Users don't edit config by hand; they ask you. To add a model provider (any OpenAI-Responses-compatible or
  Anthropic API), add it under "providers" in config.json in the format at the top of models/registry.py, then tell
  the user to /reload and pick its models with /model, which asks for the key privately. Never ask for keys in chat.
- Changes to code or settings apply after the user types /reload, which restarts zero and keeps the conversation. After a code change, check that it imports:
  `uv run --project {REPO} python -c "import zero_harness.main"`.
"""

INSTRUCTIONS = f"{BASE}{load_git()}{SELF}\n# User rules\n\n{load_user_rules()}{load_project_rules()}{load_skills()}"
