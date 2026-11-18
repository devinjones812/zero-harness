from zero_harness.ui import notes, user_input


class Live:
    """Show reasoning and the answer word by word in the live area, moving finished parts to scrollback.

    API modules call think(), end_thought(), and write() as text streams in.
    """

    def __init__(self):
        self.text, self.printed, self.thought = "", 0, ""

    def __enter__(self):
        return self

    def __exit__(self, error_type, *_):
        if error_type is None:
            commit(self.text, self.printed, final=True)
        user_input.show_live("")

    def think(self, delta: str) -> None:
        self.thought += delta
        user_input.show_live(self.thought, notes.THOUGHT_STYLE)

    def end_thought(self) -> None:
        if self.thought.strip():
            notes.thought(self.thought)
        self.thought = ""
        user_input.show_live("")

    def write(self, delta: str) -> None:
        self.text += delta
        self.printed = commit(self.text, self.printed, final=False)
        user_input.show_live(self.text[self.printed :])


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
