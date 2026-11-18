import argparse
import asyncio
import os
import shutil
import sys
import traceback

from prompt_toolkit.patch_stdout import patch_stdout

from zero_harness import (
    checkpoints,
    config,
    context,
    errors,
    images,
    jobs,
    llm,
    permissions,
    sessions,
)
from zero_harness.commands import registry as commands
from zero_harness.commands import reload
from zero_harness.tools import registry as tools
from zero_harness.ui import logo, notes, user_input
from zero_harness.ui.notes import note

inbox: asyncio.Queue[str | None] = asyncio.Queue()
turn: asyncio.Task | None = None


def main() -> None:
    parser = argparse.ArgumentParser(prog="zero", description="A coding agent for your terminal.")
    parser.add_argument("message", nargs="?", help="first message to send")
    parser.add_argument("-r", "--resume", nargs="?", const="", metavar="SESSION", help="pick a session, or give its file")
    args = parser.parse_args()
    if not sys.stdin.isatty():
        sys.exit("zero needs an interactive terminal.")
    asyncio.run(run(args))
    if reload.requested:
        restart()


def restart() -> None:
    """Replace this process with a new zero that resumes this session. exec skips atexit, so clean up first."""
    jobs.cleanup()
    shutil.rmtree(permissions.SCRATCH, ignore_errors=True)
    resume = ["--resume", str(sessions.current)] if sessions.current.exists() else []
    os.execv(sys.executable, [sys.executable, "-m", "zero_harness.main", *resume])


async def run(args: argparse.Namespace) -> None:
    """Two tasks on one event loop: the input loop keeps the prompt on screen, the agent loop runs turns."""
    history = []
    logo.show()
    note(f"zero  {config.get('model')}  {os.getcwd()}")
    note("type / for commands, Ctrl+C clears the input")
    if args.resume is not None:
        await commands.run(f"/resume {args.resume}".strip(), history)
    jobs.on_finish = lambda: inbox.put_nowait(None)
    user_input.setup(busy, list(commands.COMMANDS))
    with patch_stdout(raw=True):
        agent = asyncio.create_task(agent_loop(history))
        if args.message:
            notes.user(args.message)
            inbox.put_nowait(args.message)
        await input_loop(history)
        agent.cancel()


def busy() -> bool:
    return turn is not None and not turn.done()


async def input_loop(history: list) -> None:
    """Route what the user sends: an answer to a pending question, a /command, or a message for the agent."""
    while True:
        try:
            text = await user_input.read()
        except KeyboardInterrupt:
            if not busy():
                return
            turn.cancel()
            continue
        except EOFError:
            return
        if user_input.answer(text):
            continue
        if user_input.is_command(text):
            if busy():
                note("The agent is working. Wait for it to finish, or press Ctrl+C to stop it.")
            else:
                await commands.run(text, history)
                sessions.save(history)
                if reload.requested:
                    return
            continue
        notes.user(text)
        inbox.put_nowait(text)


async def agent_loop(history: list) -> None:
    """Wait for a message or a finished background job, then run a turn. Ctrl+C cancels only the turn."""
    global turn
    while True:
        text = await inbox.get()
        if text is None and not jobs.any_finished():
            continue
        if text:
            history.append(images.user_message(text))
        checkpoints.start()
        turn = asyncio.create_task(run_turn(history))
        try:
            await turn
            if text and not sessions.title:
                sessions.title = await llm.title(text)
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling():
                raise
            note("[interrupted] Stopped this turn.")
        except errors.RECOVERABLE as error:
            errors.report(error)
        except Exception:  # noqa: BLE001 - one failed turn must not crash zero
            note(traceback.format_exc(), style="red")
        errors.repair(history)
        sessions.save(history)


async def run_turn(history: list) -> None:
    """Call the model and run tools until it stops calling them."""
    max_rounds = config.get("max_tool_rounds")
    for _ in range(max_rounds):
        add_arrivals(history)
        await context.manage(history)
        response = await llm.respond(history)
        output = [item.model_dump(exclude_none=True) for item in response.output]
        history += output

        calls = [item for item in output if item["type"] == "function_call"]
        if not calls:
            return

        for call in calls:
            history.append(await tools.run(call))

    note(f"[limit] stopped after {max_rounds} tool rounds. Send a message to continue.")


def add_arrivals(history: list) -> None:
    """Add messages sent during the turn and finished-job notices before the next model call."""
    while not inbox.empty():
        if text := inbox.get_nowait():
            history.append(images.user_message(text))
    for short, notice in jobs.finished():
        note(short)
        history.append({"role": "user", "content": notice})


if __name__ == "__main__":
    main()
