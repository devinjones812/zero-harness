import os
from datetime import date
from pathlib import Path

from zero_harness import config

USER_RULES = Path.home() / ".cursor/rules/agents.mdc"
PROJECT_RULES = ["AGENTS.md", "CLAUDE.md"]
SKILLS = config.HOME / "skills"


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


def load_skills() -> str:
    """List each skills/<name>/SKILL.md by name and description; the agent reads the full file only when needed."""
    lines = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        text = path.read_text()
        meta = text.split("---")[1] if text.startswith("---") else ""
        description = next((line.split(":", 1)[1].strip() for line in meta.splitlines() if line.startswith("description:")), "")
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
  you get a [background] message when one finishes. Use the job tool to check output or kill it.
- web_search for current information, web_fetch to read a full page. Cite the URLs you use.

Rules:
- Act; don't ask permission. The harness asks the user before risky commands and edits.
- If the user denies an action, don't retry it. Ask what they want instead.
- If a tool returns an error, read it and fix the cause.
- The user can send messages while you work. They appear between tool calls; follow the latest one.
- Check your work: run the code or tests after you change something.
- Answers are for a terminal: short, plain text, no headers. Lead with the result.
"""

INSTRUCTIONS = f"{BASE}\n# User rules\n\n{load_user_rules()}{load_project_rules()}{load_skills()}"
