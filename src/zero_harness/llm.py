from zero_harness import config, usage
from zero_harness.models import listing, registry
from zero_harness.models.reply import Reply
from zero_harness.prompt import INSTRUCTIONS
from zero_harness.ui.stream import Live


async def respond(history: list, tools: list) -> Reply:
    """Stream one model turn to the terminal and return the reply. `tools` are the main agent's tool schemas."""
    with Live() as live:
        reply = await registry.call(instructions=INSTRUCTIONS, history=history, tools=tools, effort=effort(), live=live)
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


async def complete(history: list, tools: list) -> str:
    """Hidden text-only call for internal use, e.g. compaction summaries. Send the same `tools` as respond() so the
    prompt cache still matches."""
    reply = await registry.call(
        instructions=INSTRUCTIONS, history=history, tools=tools, effort=effort(), tool_choice="none"
    )
    usage.record(reply, conversation=False)
    return reply.text


def effort() -> str | None:
    """The reasoning level to send, or None for the provider's default."""
    return listing.level(config.get("model"), config.get("effort"))
