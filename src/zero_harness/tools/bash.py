import asyncio
import subprocess

from zero_harness import jobs, workdir
from zero_harness.permissions import approve_command
from zero_harness.ui.notes import note

DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 600

SCHEMA = {
    "type": "function",
    "name": "bash",
    "description": (
        "Run a bash command in the working directory. Returns stdout and stderr. No stdin. "
        f"Default timeout {DEFAULT_TIMEOUT}s, max {MAX_TIMEOUT}s. Raise it for slow builds or tests. "
        "Use background=true for servers, watchers, or anything longer; it returns a job id at once."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "purpose": {
                "type": "string",
                "description": "One short sentence for the user: what the command does. Shown when it needs approval.",
            },
            "timeout": {"type": "integer", "description": f"Seconds. Default {DEFAULT_TIMEOUT}, max {MAX_TIMEOUT}."},
            "background": {"type": "boolean", "description": "Run without waiting. Default false."},
        },
        "required": ["command", "purpose"],
    },
}


async def run(command: str, purpose: str = "", timeout: int = DEFAULT_TIMEOUT, background: bool = False) -> str:
    """Run in its own process group so a timeout or Ctrl+C kills the command and every child it started."""
    if background and workdir.tree.get():
        return "error: subagents can't start background jobs. Run the command with a timeout instead."
    if background:
        note("  ↳ runs in the background")
    if denied := await approve_command(command, purpose):
        return denied
    if background:
        job_id = await jobs.start(command)
        return f"started background job {job_id}. You will get a [background] message when it finishes."
    timeout = min(timeout, MAX_TIMEOUT)
    process = await asyncio.create_subprocess_shell(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=workdir.root(),
        start_new_session=True,
    )
    chunks = []

    async def collect() -> None:
        while chunk := await process.stdout.read(65536):
            chunks.append(chunk)

    try:
        await asyncio.wait_for(asyncio.gather(collect(), process.wait()), timeout)
        ending = ""
    except TimeoutError:
        jobs.kill_group(process)
        ending = f"\n(timed out after {timeout}s and was killed)"
    except asyncio.CancelledError:
        jobs.kill_group(process)
        raise
    return b"".join(chunks).decode(errors="replace") + ending
