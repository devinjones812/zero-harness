import subprocess

MAX_MATCHES = 100

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
        ["rg", "--line-number", "--no-heading", "--color=never", "--max-columns=300", "-e", pattern, path],
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
