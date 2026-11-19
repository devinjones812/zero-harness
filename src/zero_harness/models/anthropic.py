"""Anthropic's Messages API. Converts history (Responses-API items) to messages, and replies back to items.

Targets Claude models with adaptive thinking and effort levels (Claude Opus 4.6 and later).
"""

import json
from typing import TYPE_CHECKING

from zero_harness.models.reply import Reply, Usage

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

# A hard limit on thinking plus text. Anthropic suggests 64k to start at xhigh and max effort.
MAX_TOKENS = 64_000
THINKING = ("thinking", "redacted_thinking")


def client(base_url: str | None, key: str) -> AsyncAnthropic:
    from anthropic import AsyncAnthropic

    return AsyncAnthropic(base_url=base_url, api_key=key, max_retries=4)


async def list_models(client: AsyncAnthropic) -> list[str]:
    return [model.id async for model in client.models.list()]


async def call(client: AsyncAnthropic, model: str, *, instructions, history, tools, effort, tool_choice, live) -> Reply:
    request = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": instructions,
        "messages": messages(history),
        "thinking": {"type": "adaptive", "display": "summarized"},
        # Caches everything up to the last block, and moves forward as history grows.
        "cache_control": {"type": "ephemeral"},
    }
    if tools:
        request["tools"] = [
            {"name": tool["name"], "description": tool["description"], "input_schema": tool["parameters"]}
            for tool in tools
        ]
    if effort:
        request["output_config"] = {"effort": effort}
    if tool_choice:
        request["tool_choice"] = {"type": tool_choice}
    # Always stream: the SDK refuses long non-streaming requests.
    async with client.messages.stream(**request) as stream:
        async for event in stream:
            if live is None:
                continue
            if event.type == "thinking":
                live.think(event.thinking)
            elif event.type == "text":
                live.write(event.text)
            elif event.type == "content_block_stop" and event.content_block.type in THINKING:
                live.end_thought()
        message = await stream.get_final_message()
    usage = message.usage
    cached, written = usage.cache_read_input_tokens or 0, usage.cache_creation_input_tokens or 0
    return Reply(
        model=message.model,
        output=[item(block) for block in message.content],
        usage=Usage(
            input_tokens=usage.input_tokens + cached + written,
            cached_tokens=cached,
            output_tokens=usage.output_tokens,
            cache_write_tokens=written,
        ),
    )


def item(block) -> dict:
    """A content block as a Responses-API item."""
    if block.type == "text":
        return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": block.text}]}
    if block.type == "tool_use":
        return {"type": "function_call", "call_id": block.id, "name": block.name, "arguments": json.dumps(block.input)}
    # Thinking blocks must go back unchanged in tool loops, so keep the whole block.
    return {
        "type": "reasoning",
        "summary": [{"type": "summary_text", "text": getattr(block, "thinking", "")}],
        "api": "anthropic",
        "block": block.model_dump(exclude_none=True),
    }


def messages(history: list) -> list[dict]:
    """History items as alternating user and assistant messages."""
    result = []

    def add(role: str, block: dict) -> None:
        if result and result[-1]["role"] == role:
            result[-1]["content"].append(block)
        else:
            result.append({"role": role, "content": [block]})

    for entry in history:
        kind = entry.get("type")
        if kind == "reasoning":
            # Other APIs' reasoning has no signature, so Claude can't use it.
            if entry.get("api") == "anthropic":
                add("assistant", entry["block"])
        elif kind == "function_call":
            call = {"type": "tool_use", "id": entry["call_id"], "name": entry["name"]}
            add("assistant", call | {"input": json.loads(entry["arguments"] or "{}")})
        elif kind == "function_call_output":
            output = entry["output"]
            # read_file returns images as a list of parts.
            output = output if isinstance(output, str) else content(output)
            add("user", {"type": "tool_result", "tool_use_id": entry["call_id"], "content": output})
        else:
            for block in content(entry["content"]):
                add(entry["role"], block)
    return result


def content(parts: str | list) -> list[dict]:
    """Message text and data-URL images as Anthropic content blocks. Empty text is dropped; the API rejects it."""
    if isinstance(parts, str):
        parts = [{"type": "input_text", "text": parts}]
    blocks = []
    for part in parts:
        if part.get("text"):
            blocks.append({"type": "text", "text": part["text"]})
        elif part["type"] == "input_image":
            header, _, data = part["image_url"].partition(",")
            media_type = header.removeprefix("data:").removesuffix(";base64")
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}})
    return blocks
