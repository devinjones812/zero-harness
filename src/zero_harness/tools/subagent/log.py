"""A subagent's live log: what it thinks, says, and does, for /watch to follow in another window."""

from pathlib import Path

from zero_harness.ui.notes import summary

THOUGHT, TOOL, BOLD, DIM, RESET = "\x1b[2;3m", "\x1b[36m", "\x1b[1m", "\x1b[2m", "\x1b[0m"
MAX_OUTPUT_LINES = 20


class Log:
    """Takes the model's stream like ui.stream.Live does (think, end_thought, write), plus each tool call."""

    def __init__(self, path: Path, header: str):
        self.file = path.open("w", buffering=1)  # line-buffered, so a follower sees each line as it comes
        self.thinking = False
        self.file.write(f"{BOLD}{header}{RESET}\n\n")

    def think(self, delta: str) -> None:
        if not self.thinking:
            self.file.write(THOUGHT)
            self.thinking = True
        self.file.write(delta)

    def end_thought(self) -> None:
        if self.thinking:
            self.file.write(f"{RESET}\n\n")
            self.thinking = False

    def write(self, delta: str) -> None:
        self.end_thought()
        self.file.write(delta)

    def tool(self, name: str, args: dict, output) -> None:
        self.end_thought()
        lines = output.splitlines() if isinstance(output, str) else ["(image)"]
        shown = "\n".join(f"  {line}" for line in lines[:MAX_OUTPUT_LINES])
        more = f"\n  … {len(lines) - MAX_OUTPUT_LINES} more lines" if len(lines) > MAX_OUTPUT_LINES else ""
        self.file.write(f"\n{TOOL}● {name}{RESET}  {summary(args)}\n{DIM}{shown}{more}{RESET}\n\n")

    def close(self, line: str) -> None:
        self.end_thought()
        self.file.write(f"\n\n{BOLD}{line}{RESET}\n")
        self.file.close()
