import os
import sys

from dotenv import load_dotenv
from openai import AsyncOpenAI

from zero_harness import config, usage
from zero_harness.prompt import INSTRUCTIONS
from zero_harness.tools import registry
from zero_harness.ui.stream import print_stream

load_dotenv(config.HOME / ".env")
if not os.getenv("OPENAI_API_KEY"):
    sys.exit(f"zero: set OPENAI_API_KEY in {config.HOME / '.env'} (see .env.example in the repo).")
client = AsyncOpenAI(max_retries=4)


async def respond(history: list):
    """Stream one model turn to the terminal and return the completed response."""
    stream = await client.responses.create(
        model=config.get("model"), instructions=INSTRUCTIONS, input=history, tools=registry.SCHEMAS, stream=True
    )
    response = await print_stream(stream)
    usage.record(response)
    return response


async def title(text: str) -> str:
    """Short nickname for a session, from its first message."""
    response = await client.responses.create(
        model=config.get("model"),
        instructions="Write a 3-6 word title for a coding session that starts with this message. Title only.",
        input=text[:2000],
    )
    usage.record(response, conversation=False)
    return response.output_text.strip().strip('"')


async def complete(history: list) -> str:
    """Hidden text-only call for internal use, e.g. compaction summaries."""
    response = await client.responses.create(
        model=config.get("model"),
        instructions=INSTRUCTIONS,
        input=history,
        tools=registry.SCHEMAS,
        tool_choice="none",
    )
    usage.record(response, conversation=False)
    return response.output_text
