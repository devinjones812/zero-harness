import json

from anthropic.types import (
    RedactedThinkingBlock,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)

from zero_harness.models.anthropic import item, messages

IMAGE = {"type": "input_image", "image_url": "data:image/png;base64,AAAA"}
IMAGE_BLOCK = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}}


def test_tool_loop_becomes_alternating_messages():
    history = [
        {"role": "user", "content": "read it"},
        {"type": "function_call", "call_id": "c1", "name": "read_file", "arguments": '{"path": "a.py"}'},
        {"type": "function_call", "call_id": "c2", "name": "grep", "arguments": ""},
        {"type": "function_call_output", "call_id": "c1", "output": "one"},
        {"type": "function_call_output", "call_id": "c2", "output": "two"},
        {"role": "user", "content": "sent while working"},
    ]
    assert messages(history) == [
        {"role": "user", "content": [{"type": "text", "text": "read it"}]},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "c1", "name": "read_file", "input": {"path": "a.py"}},
                {"type": "tool_use", "id": "c2", "name": "grep", "input": {}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "c1", "content": "one"},
                {"type": "tool_result", "tool_use_id": "c2", "content": "two"},
                {"type": "text", "text": "sent while working"},
            ],
        },
    ]


def test_images_in_messages_and_tool_results():
    history = [
        {"role": "user", "content": [{"type": "input_text", "text": "look"}, IMAGE]},
        {"type": "function_call", "call_id": "c1", "name": "read_file", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c1", "output": [IMAGE]},
    ]
    converted = messages(history)
    assert converted[0]["content"] == [{"type": "text", "text": "look"}, IMAGE_BLOCK]
    assert converted[2]["content"] == [{"type": "tool_result", "tool_use_id": "c1", "content": [IMAGE_BLOCK]}]


def test_assistant_text_and_empty_text():
    history = [
        {"role": "user", "content": [{"type": "input_text", "text": ""}, {"type": "input_text", "text": "hi"}]},
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "hello"}]},
        {"role": "user", "content": "bye"},
    ]
    assert messages(history) == [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "hello"}]},
        {"role": "user", "content": [{"type": "text", "text": "bye"}]},
    ]


def test_only_claude_reasoning_goes_back():
    thinking = {"type": "thinking", "thinking": "", "signature": "sig"}
    history = [
        {"role": "user", "content": "go"},
        {"type": "reasoning", "id": "rs_openai", "summary": []},
        {"type": "reasoning", "summary": [], "api": "anthropic", "block": thinking},
        {"type": "function_call", "call_id": "c1", "name": "grep", "arguments": "{}"},
    ]
    assert messages(history)[1]["content"] == [thinking, {"type": "tool_use", "id": "c1", "name": "grep", "input": {}}]


def test_reply_blocks_become_history_items():
    tool = ToolUseBlock(type="tool_use", id="c1", name="grep", input={"pattern": "x"})
    assert item(TextBlock(type="text", text="hi")) == {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "hi"}],
    }
    assert item(tool) == {"type": "function_call", "call_id": "c1", "name": "grep", "arguments": json.dumps({"pattern": "x"})}
    thought = item(ThinkingBlock(type="thinking", thinking="plan", signature="sig"))
    assert thought["api"] == "anthropic"
    assert thought["block"] == {"type": "thinking", "thinking": "plan", "signature": "sig"}
    assert item(RedactedThinkingBlock(type="redacted_thinking", data="x"))["block"]["data"] == "x"


def test_round_trip_keeps_blocks_unchanged():
    blocks = [
        ThinkingBlock(type="thinking", thinking="plan", signature="sig"),
        TextBlock(type="text", text="checking"),
        ToolUseBlock(type="tool_use", id="c1", name="grep", input={"pattern": "x"}),
    ]
    history = [{"role": "user", "content": "go"}, *[item(block) for block in blocks]]
    assert messages(history)[1]["content"] == [
        {"type": "thinking", "thinking": "plan", "signature": "sig"},
        {"type": "text", "text": "checking"},
        {"type": "tool_use", "id": "c1", "name": "grep", "input": {"pattern": "x"}},
    ]
