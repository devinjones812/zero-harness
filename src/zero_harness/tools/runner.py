import asyncio
import inspect
import json

from zero_harness.ui.notes import note, summary, tool

MAX_RESULT_CHARS = 20_000


async def run(call: dict, functions: dict, show: bool = True) -> dict:
    """Run a model's function_call. Errors go back to the model as text so the loop continues.

    Async tools are awaited; plain ones run in a worker thread so they don't block the prompt. `show` prints the
    tool line and errors; subagents run quietly.
    """
    try:
        args = json.loads(call["arguments"])
        if show and call["name"] != "todo":
            tool(call["name"], summary(args))
        function = functions[call["name"]]
        if inspect.iscoroutinefunction(function):
            output = await function(**args)
        else:
            output = await asyncio.to_thread(function, **args)
    except Exception as error:  # noqa: BLE001 - tool errors go back to the model as text
        output = f"error: {error}"
        if show:
            note(f"  {output}", style="red")
    if isinstance(output, str):
        output = cap(output, show)
    return {"type": "function_call_output", "call_id": call["call_id"], "output": output}


def cap(output: str, show: bool = True) -> str:
    """Cut a tool result to MAX_RESULT_CHARS and tell the model it was cut."""
    if len(output) <= MAX_RESULT_CHARS:
        return output
    if show:
        note(f"[context] cap: tool result was {len(output):,} chars (limit {MAX_RESULT_CHARS:,}). Cut it.")
    return output[:MAX_RESULT_CHARS] + (
        f"\n(output cut at {MAX_RESULT_CHARS} of {len(output)} chars. "
        "Narrow the request, e.g. read_file offset/limit or a tighter grep.)"
    )
