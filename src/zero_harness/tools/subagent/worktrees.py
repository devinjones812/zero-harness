"""Git worktrees for editing subagents: each gets a copy of the user's current files, and its changes merge back
file by file."""

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from zero_harness import checkpoints
from zero_harness.permissions import SCRATCH
from zero_harness.workdir import Tree

# Ignored folders that tests need, linked from the user's repo so a worktree can run them. Shared, not copied.
DEPENDENCIES = [".venv", "venv", "node_modules"]
# Never merged back: the linked folders, and build files a subagent's test run leaves even where git doesn't ignore them.
JUNK = ["**/__pycache__/**", "**/*.pyc", "**/.pytest_cache/**", "**/.DS_Store"]
SKIP = [f":(exclude){name}" for name in DEPENDENCIES] + [f":(exclude,glob){pattern}" for pattern in JUNK]


def git(*args: str, cwd: Path, env: dict | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def repo(cwd: Path) -> Path | None:
    """The top of the git repo that contains `cwd`, or None."""
    try:
        return Path(git("rev-parse", "--show-toplevel", cwd=cwd)).resolve()
    except RuntimeError:
        return None


def snapshot(top: Path) -> str:
    """Commit the user's current files, uncommitted and untracked ones too, without touching their branch, index,
    or files. Ignored files such as .env stay out."""
    with tempfile.TemporaryDirectory() as folder:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(folder) / "index")}
        try:
            parent = ["-p", git("rev-parse", "--verify", "HEAD", cwd=top)]
            git("read-tree", "HEAD", cwd=top, env=env)
        except RuntimeError:  # a repo with no commits yet
            parent = []
        git("add", "-A", cwd=top, env=env)
        tree = git("write-tree", cwd=top, env=env)
        return git("commit-tree", tree, *parent, "-m", "zero subagent snapshot", cwd=top)


def create(top: Path, base: str, label: str) -> Tree:
    """A worktree of `base`, with the user's dependency folders linked in, standing in for the working directory."""
    folder = SCRATCH / f"worktree-{uuid.uuid4().hex[:8]}"
    git("worktree", "add", "--detach", str(folder), base, cwd=top)
    for name in DEPENDENCIES:
        if (top / name).is_dir() and not (folder / name).exists():
            (folder / name).symlink_to(top / name)
    return Tree(label=label, repo=top, top=folder, root=folder / Path.cwd().resolve().relative_to(top))


def remove(tree: Tree) -> None:
    try:
        git("worktree", "remove", "--force", str(tree.top), cwd=tree.repo)
    except RuntimeError:
        shutil.rmtree(tree.top, ignore_errors=True)
        git("worktree", "prune", cwd=tree.repo)


def changes(tree: Tree, base: str) -> list[str]:
    """Paths (from the repo top) the subagent added, changed, or deleted."""
    git("add", "-A", "--", ".", *SKIP, cwd=tree.top)
    return git("diff", "--cached", "--name-only", "--no-renames", base, cwd=tree.top).splitlines()


def diff(tree: Tree, base: str, paths: list[str]) -> str:
    return git("diff", "--cached", "--no-renames", base, "--", *paths, cwd=tree.top)


def plan(tree: Tree, base: str) -> tuple[dict[str, bytes | None], list[str]]:
    """What merging the subagent's changes would write: {path: new content, or None to delete}, and the paths that
    conflict with changes the user or another subagent made since the snapshot."""
    writes, conflicts = {}, []
    for path in changes(tree, base):
        original, current, new = shown(tree.repo, base, path), read(tree.repo / path), read(tree.top / path)
        if current in (original, new):
            writes[path] = new
        elif None not in (original, current, new) and (merged := merge(original, current, new)) is not None:
            writes[path] = merged
        else:
            conflicts.append(path)
    return writes, conflicts


def apply(top: Path, writes: dict[str, bytes | None]) -> None:
    """Write a plan to the user's files. /undo restores them as one step."""
    checkpoints.start()
    for path, content in writes.items():
        file = top / path
        checkpoints.record(str(file))
        if content is None:
            file.unlink(missing_ok=True)
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(content)


def shown(top: Path, base: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{base}:{path}"], cwd=top, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def read(file: Path) -> bytes | None:
    return file.read_bytes() if file.is_file() else None


def merge(original: bytes, current: bytes, new: bytes) -> bytes | None:
    """A 3-way merge of one file, or None if the two sides changed the same lines."""
    with tempfile.TemporaryDirectory() as folder:
        files = []
        for name, content in (("current", current), ("original", original), ("new", new)):
            files.append(Path(folder) / name)
            files[-1].write_bytes(content)
        result = subprocess.run(["git", "merge-file", "-p", *map(str, files)], capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None
