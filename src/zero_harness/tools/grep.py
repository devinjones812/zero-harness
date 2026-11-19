import subprocess
import sys
from pathlib import Path

from zero_harness import workdir

MAX_MATCHES = 100
# The ripgrep dependency installs rg into zero's own environment, which uv tool does not put on PATH.
RG = Path(sys.executable).parent / "rg"

SCHEMA = {
    "type": "function",
    "name": "grep",
    "description": (
        "Search file contents with ripgrep (Rust regex syntax). Skips hidden and .gitignore'd files. "
        "Returns matches as path:line:text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string", "description": "File or directory to search. Default: current directory."},
        },
        "required": ["pattern"],
    },
}


def run(pattern: str, path: str = ".") -> str:
    result = subprocess.run(
        [RG, "--line-number", "--no-heading", "--color=never", "--max-columns=300", "-e", pattern, searched(path)],
        cwd=workdir.root(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return f"error: {result.stderr.strip()}"
    lines = result.stdout.splitlines()
    if len(lines) > MAX_MATCHES:
        return "\n".join(lines[:MAX_MATCHES]) + f"\n(stopped at {MAX_MATCHES} of {len(lines)} matches)"
    return result.stdout or "no matches"


def searched(path: str) -> str:
    """Relative paths stay relative, so matches print short; absolute ones may map into a worktree."""
    return path if not Path(path).expanduser().is_absolute() else str(workdir.resolve(path))
