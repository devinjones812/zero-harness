import asyncio
import subprocess

import pytest

from zero_harness import checkpoints, config, workdir
from zero_harness.tools import edit_file
from zero_harness.tools.subagent import worktrees

LINES = "".join(f"line {n}\n" for n in range(1, 21))


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo with one commit, an uncommitted change, an untracked file, an ignored secret, and a .venv."""
    git("init", "-q", cwd=tmp_path)
    git("config", "user.email", "t@t", cwd=tmp_path)
    git("config", "user.name", "t", cwd=tmp_path)
    (tmp_path / ".gitignore").write_text(".env\n.venv/\n")
    (tmp_path / "a.py").write_text(LINES)
    git("add", "-A", cwd=tmp_path)
    git("commit", "-qm", "start", cwd=tmp_path)
    (tmp_path / "a.py").write_text(LINES.replace("line 1\n", "line 1 uncommitted\n"))
    (tmp_path / "new.py").write_text("untracked\n")
    (tmp_path / ".env").write_text("SECRET=1\n")
    (tmp_path / ".venv").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path.resolve()


@pytest.fixture
def tree(repo):
    base = worktrees.snapshot(repo)
    made = worktrees.create(repo, base, "subagent 1")
    yield made, base
    worktrees.remove(made)


def test_worktree_has_the_users_current_files_but_not_secrets(repo, tree):
    made, _ = tree
    assert (made.top / "a.py").read_text().startswith("line 1 uncommitted")
    assert (made.top / "new.py").exists()
    assert not (made.top / ".env").exists()
    assert (made.top / ".venv").resolve() == repo / ".venv"
    status = subprocess.run(["git", "status", "--short"], check=True, cwd=repo, capture_output=True, text=True).stdout
    assert " M a.py" in status and "?? new.py" in status  # the user's index is untouched


def test_paths_into_the_users_repo_map_into_the_worktree(repo, tree):
    made, _ = tree
    token = workdir.tree.set(made)
    try:
        assert workdir.resolve(str(repo / "a.py")) == made.top / "a.py"
        assert workdir.resolve("a.py") == made.root / "a.py"
    finally:
        workdir.tree.reset(token)


def test_subagent_edits_need_no_approval_and_stay_in_the_worktree(repo, tree, monkeypatch):
    made, base = tree
    monkeypatch.setitem(config.saved, "mode", "ask")
    token = workdir.tree.set(made)
    try:
        assert asyncio.run(edit_file.run("a.py", "line 20\n", "line 20 agent\n")) == "ok"
    finally:
        workdir.tree.reset(token)
    assert "agent" not in (repo / "a.py").read_text()
    (made.top / "__pycache__").mkdir()
    (made.top / "__pycache__" / "a.cpython-314.pyc").write_bytes(b"\0")
    assert worktrees.changes(made, base) == ["a.py"]  # no build files, no linked .venv


def test_merges_changes_to_other_lines_and_undo_restores(repo, tree):
    made, base = tree
    (made.top / "a.py").write_text((made.top / "a.py").read_text().replace("line 20\n", "line 20 agent\n"))
    (made.top / "added.py").write_text("by agent\n")
    (repo / "a.py").write_text((repo / "a.py").read_text().replace("line 2\n", "line 2 user\n"))
    writes, conflicts = worktrees.plan(made, base)
    assert conflicts == [] and set(writes) == {"a.py", "added.py"}
    checkpoints.start()
    worktrees.apply(repo, writes)
    merged = (repo / "a.py").read_text()
    assert "line 1 uncommitted" in merged and "line 2 user" in merged and "line 20 agent" in merged
    assert (repo / "added.py").read_text() == "by agent\n"
    checkpoints.undo()
    assert "line 20 agent" not in (repo / "a.py").read_text() and not (repo / "added.py").exists()


def test_same_line_changed_on_both_sides_is_a_conflict(repo, tree):
    made, base = tree
    (made.top / "a.py").write_text((made.top / "a.py").read_text().replace("line 5\n", "line 5 agent\n"))
    (repo / "a.py").write_text((repo / "a.py").read_text().replace("line 5\n", "line 5 user\n"))
    assert worktrees.plan(made, base) == ({}, ["a.py"])
