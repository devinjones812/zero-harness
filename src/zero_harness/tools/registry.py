import asyncio

from zero_harness.tools import (
    agent,
    bash,
    edit_file,
    grep,
    job,
    read_file,
    runner,
    todo,
    web_fetch,
    web_search,
)

TOOLS = [bash, job, read_file, edit_file, grep, web_search, web_fetch, todo, agent]

SCHEMAS = [tool.SCHEMA for tool in TOOLS]
FUNCTIONS = {tool.SCHEMA["name"]: tool.run for tool in TOOLS}


async def run(call: dict) -> dict:
    return await runner.run(call, FUNCTIONS)


async def run_all(calls: list[dict]) -> list[dict]:
    """Run one reply's calls and return their outputs in order. Subagents run together; other tools run one at a
    time, since they may ask the user for approval."""
    subagents = {call["call_id"]: asyncio.create_task(run(call)) for call in calls if call["name"] == "agent"}
    try:
        outputs = {call["call_id"]: await run(call) for call in calls if call["name"] != "agent"}
        for call_id, task in subagents.items():
            outputs[call_id] = await task
    finally:
        for task in subagents.values():
            task.cancel()
    return [outputs[call["call_id"]] for call in calls]
