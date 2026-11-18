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
    if not sys.stdin.isatty():
        sys.exit(f"zero: set OPENAI_API_KEY in {config.HOME / '.env'}.")
    print("zero needs an OpenAI API key. Create one at https://platform.openai.com/api-keys")
    key = input("Paste your key and press Enter: ").strip()
    if not key:
        sys.exit("zero: no key entered.")
    config.HOME.mkdir(parents=True, exist_ok=True)
    env_file = config.HOME / ".env"
    with env_file.open("a") as file:
        file.write(f"\nOPENAI_API_KEY={key}\n")
    env_file.chmod(0o600)
    os.environ["OPENAI_API_KEY"] = key
    print(f"Saved to {env_file}.\n")
client = AsyncOpenAI(max_retries=4)


async def respond(history: list):
    """Stream one model turn to the terminal and return the completed response."""
    stream = await client.responses.create(
        model=config.get("model"),
        instructions=INSTRUCTIONS,
        input=history,
        tools=registry.SCHEMAS,
        stream=True,
        reasoning={"effort": config.get("effort"), "summary": "auto"},
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
        reasoning={"effort": config.get("effort")},
    )
    usage.record(response, conversation=False)
    return response.output_text
