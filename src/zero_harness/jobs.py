import asyncio
import atexit
import contextlib
import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

TAIL_CHARS = 2000


@dataclass
class Job:
    command: str
    process: asyncio.subprocess.Process
    log: Path
    watcher: asyncio.Task
    reported: bool = False


jobs: dict[int, Job] = {}


def on_finish() -> None:
    """Called when a job exits. main replaces it to wake the agent."""


async def start(command: str) -> int:
    """Start a command in the background. Output goes to a log file; on_finish() runs when it exits."""
    log = Path(tempfile.mkstemp(prefix="zero-harness-job-", suffix=".log")[1])
    with log.open("w") as out:
        process = await asyncio.create_subprocess_shell(
            command, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True
        )
    job_id = len(jobs) + 1

    async def watch() -> None:
        await process.wait()
        if not jobs[job_id].reported:
            on_finish()

    jobs[job_id] = Job(command, process, log, asyncio.create_task(watch()))
    return job_id


def status(job_id: int) -> str:
    job = jobs[job_id]
    code = job.process.returncode
    state = "running" if code is None else f"exited with code {code}"
    output = job.log.read_text(errors="replace")[-TAIL_CHARS:]
    return f"job {job_id} `{job.command}`: {state}\n{output}"


def kill(job_id: int) -> str:
    job = jobs[job_id]
    job.reported = True
    kill_group(job.process)
    return f"job {job_id} killed"


def kill_group(process) -> None:
    """Kill a process started with start_new_session=True, and every child it started."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


def any_finished() -> bool:
    return any(not job.reported and job.process.returncode is not None for job in jobs.values())


def finished() -> list[str]:
    """Return one notice per job that finished since the last check."""
    notices = []
    for job_id, job in jobs.items():
        if not job.reported and job.process.returncode is not None:
            job.reported = True
            notices.append(f"[background] {status(job_id)}")
    return notices


@atexit.register
def cleanup() -> None:
    """Kill running jobs and delete their logs when the harness exits."""
    for job in jobs.values():
        if job.process.returncode is None:
            kill_group(job.process)
        job.log.unlink(missing_ok=True)
