from zero_harness.errors import StreamError
from zero_harness.ui import notes, user_input


async def print_stream(stream):
    """Show the answer word by word in the live area, moving each finished block to scrollback.

    Returns the completed response.
    """
    text, printed = "", 0
    async with stream:
        try:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    text += event.delta
                    printed = commit(text, printed, final=False)
                    user_input.show_live(text[printed:])
                elif event.type == "response.completed":
                    commit(text, printed, final=True)
                    return event.response
        finally:
            user_input.show_live("")
    raise StreamError("stream ended without a completed response")


def commit(text: str, printed: int, final: bool) -> int:
    """Print the blocks after `printed` that are finished, or everything if `final`. Returns the new offset."""
    pending = text[printed:]
    end = len(pending) if final else finished_blocks(pending)
    if pending[:end].strip():
        if printed == 0:
            notes.section()
        else:
            notes.console.print()
        notes.answer(pending[:end])
    return printed + end


def finished_blocks(text: str) -> int:
    """Length of the text up to its last blank line outside a code fence. A block can't change after that."""
    end, position, in_fence = 0, 0, False
    for line in text.splitlines(keepends=True):
        position += len(line)
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and not line.strip() and line.endswith("\n"):
            end = position
    return end
