"""OpenAI's Responses API, also served by many compatible providers. History is already in its format."""

from openai import AsyncOpenAI

from zero_harness.errors import StreamError
from zero_harness.models.reply import Reply, Usage


def client(base_url: str | None, key: str) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=base_url, api_key=key, max_retries=4)


async def list_models(client: AsyncOpenAI) -> list[str]:
    return [model.id async for model in client.models.list()]


async def call(client: AsyncOpenAI, model: str, *, instructions, history, tools, effort, tool_choice, live) -> Reply:
    request = {
        "model": model,
        "instructions": instructions,
        # Reasoning items from other APIs carry an "api" tag. This API can't read them.
        "input": [item for item in history if not item.get("api")],
        "tools": tools,
    }
    if effort:
        request["reasoning"] = {"effort": effort, "summary": "auto"}
    if tool_choice:
        request["tool_choice"] = tool_choice
    if live is None:
        response = await client.responses.create(**request)
    else:
        response = await read(await client.responses.create(**request, stream=True), live)
    usage = response.usage
    return Reply(
        model=response.model,
        # Some compatible providers return reasoning summaries as plain strings, which makes pydantic print warnings.
        output=[item.model_dump(exclude_none=True, warnings=False) for item in response.output],
        usage=Usage(
            input_tokens=usage.input_tokens,
            # Some compatible providers omit input_tokens_details.
            cached_tokens=usage.input_tokens_details.cached_tokens if usage.input_tokens_details else 0,
            output_tokens=usage.output_tokens,
        ),
    )


async def read(stream, live):
    """Pass reasoning and answer text to `live` as they stream. Returns the completed response."""
    async with stream:
        async for event in stream:
            # Some compatible providers stream reasoning as response.reasoning.delta, with no part.done.
            if event.type in ("response.reasoning_summary_text.delta", "response.reasoning.delta"):
                live.think(event.delta)
            elif event.type == "response.reasoning_summary_part.done" or (
                event.type == "response.output_item.done" and event.item.type == "reasoning"
            ):
                live.end_thought()
            elif event.type == "response.output_text.delta":
                live.write(event.delta)
            elif event.type == "response.completed":
                return event.response
    raise StreamError("stream ended without a completed response")
