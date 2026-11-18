import asyncio
from types import SimpleNamespace

from zero_harness.models import responses


class FakeClient:
    """Records the request and returns a minimal response."""

    def __init__(self):
        self.request = None
        self.responses = SimpleNamespace(create=self.create)

    async def create(self, **request):
        self.request = request
        usage = SimpleNamespace(input_tokens=10, input_tokens_details=None, output_tokens=2)
        return SimpleNamespace(model="m", output=[], usage=usage)


def test_drops_other_apis_reasoning_and_handles_missing_details():
    client = FakeClient()
    history = [
        {"role": "user", "content": "hi"},
        {"type": "reasoning", "id": "rs_1", "summary": []},
        {"type": "reasoning", "summary": [], "api": "anthropic", "block": {}},
    ]
    reply = asyncio.run(
        responses.call(
            client, "m", instructions="", history=history, tools=[], effort=None, tool_choice=None, live=None
        )
    )
    assert client.request["input"] == history[:2]
    assert "reasoning" not in client.request
    assert reply.usage.cached_tokens == 0
