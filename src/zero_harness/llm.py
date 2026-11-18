from zero_harness import config, usage
from zero_harness.models import listing, registry
from zero_harness.models.reply import Reply
from zero_harness.prompt import INSTRUCTIONS
from zero_harness.tools import registry as tools
from zero_harness.ui.stream import Live


async def respond(history: list) -> Reply:
    """Stream one model turn to the terminal and return the reply."""
    with Live() as live:
        reply = await registry.call(
            instructions=INSTRUCTIONS, history=history, tools=tools.SCHEMAS, effort=effort(), live=live
        )
    usage.record(reply)
    return reply


async def title(text: str) -> str:
    """Short nickname for a session, from its first message."""
    reply = await registry.call(
        instructions="Write a 3-6 word title for a coding session that starts with this message. Title only.",
        history=[{"role": "user", "content": text[:2000]}],
    )
    usage.record(reply, conversation=False)
    return reply.text.strip().strip('"')


async def complete(history: list) -> str:
    """Hidden text-only call for internal use, e.g. compaction summaries."""
    reply = await registry.call(
        instructions=INSTRUCTIONS, history=history, tools=tools.SCHEMAS, effort=effort(), tool_choice="none"
    )
    usage.record(reply, conversation=False)
    return reply.text


def effort() -> str | None:
    """The reasoning level to send. None for models that don't reason, which reject one."""
    return config.get("effort") if listing.efforts(config.get("model")) else None
