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
