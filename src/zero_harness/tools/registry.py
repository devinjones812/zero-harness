import asyncio
import inspect
import json

from zero_harness.tools import (
    bash,
    edit_file,
    grep,
    job,
    read_file,
    todo,
    web_fetch,
    web_search,
)
from zero_harness.ui.notes import note, tool

TOOLS = [bash, job, read_file, edit_file, grep, web_search, web_fetch, todo]

SCHEMAS = [tool.SCHEMA for tool in TOOLS]
FUNCTIONS = {tool.SCHEMA["name"]: tool.run for tool in TOOLS}

MAX_RESULT_CHARS = 20_000


async def run(call: dict) -> dict:
    """Run a model's function_call. Errors go back to the model as text so the loop continues.

    Async tools are awaited; plain ones run in a worker thread so they don't block the prompt.
    """
    try:
        args = json.loads(call["arguments"])
        if call["name"] != "todo":
            tool(call["name"], summary(args))
        function = FUNCTIONS[call["name"]]
        if inspect.iscoroutinefunction(function):
            output = await function(**args)
        else:
            output = await asyncio.to_thread(function, **args)
    except Exception as error:  # noqa: BLE001 - tool errors go back to the model as text
        output = f"error: {error}"
        note(f"  {output}", style="red")
    if isinstance(output, str):
        output = cap(output)
    return {"type": "function_call_output", "call_id": call["call_id"], "output": output}


def summary(args: dict) -> str:
    """The first argument on one line, e.g. the command or path. Enough to see what the tool is doing."""
    return str(next((value for key, value in args.items() if key != "purpose"), "")).replace("\n", " ")


def cap(output: str) -> str:
    """Cut a tool result to MAX_RESULT_CHARS and tell the model it was cut."""
    if len(output) <= MAX_RESULT_CHARS:
        return output
    note(f"[context] cap: tool result was {len(output):,} chars (limit {MAX_RESULT_CHARS:,}). Cut it.")
    return output[:MAX_RESULT_CHARS] + (
        f"\n(output cut at {MAX_RESULT_CHARS} of {len(output)} chars. "
        "Narrow the request, e.g. read_file offset/limit or a tighter grep.)"
    )
