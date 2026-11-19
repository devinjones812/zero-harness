"""The folder tools work in. The main agent works in the real working directory. An editing subagent works in its
own git worktree, set for its task only, so parallel subagents don't touch each other or the user's files."""

from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Tree:
    label: str  # shown in approval prompts, e.g. "subagent 2"
    repo: Path  # top of the user's git repo
    top: Path  # top of the worktree, a copy of `repo`
    root: Path  # the folder in `top` that stands in for the working directory


tree: ContextVar[Tree | None] = ContextVar("tree", default=None)


def root() -> Path:
    """The working directory for the current task."""
    current = tree.get()
    return current.root if current else Path.cwd()


def resolve(path: str) -> Path:
    """A tool's path as an absolute path. In a worktree, absolute paths into the user's repo map into the worktree,
    so a brief that names the real files can't edit them."""
    file = Path(path).expanduser()
    if not file.is_absolute():
        return root() / file
    current = tree.get()
    if current and file.is_relative_to(current.repo):
        return current.top / file.relative_to(current.repo)
    return file
