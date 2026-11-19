import io

import rich.console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.table import Table
from rich.text import Text


class Console(rich.console.Console):
    """Keeps every print call, so a resize or /history can render them again at the current width."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.printed = []
        self.keep = True

    def print(self, *objects, **kwargs) -> None:
        if self.keep:
            self.printed.append((objects, kwargs))
        super().print(*objects, **kwargs)

    def printed_lines(self, max_lines: int | None = None) -> list[str]:
        """Everything printed, as ANSI lines at the current width. With max_lines, renders newest first and
        stops once it has more than max_lines, so a long session costs no more than a short one."""
        chunks, count = [], 0
        self.keep = False
        try:
            for objects, kwargs in reversed(self.printed):
                with self.capture() as capture:
                    super().print(*objects, **kwargs)
                chunks.append(capture.get().splitlines())
                count += len(chunks[-1])
                if max_lines and count > max_lines:
                    break
        finally:
            self.keep = True
        return [line for chunk in reversed(chunks) for line in chunk]


class Wrapped:
    """Markdown rendered when printed, so a reprint wraps it to the terminal's current width."""

    def __init__(self, text: str, style: str = "none"):
        self.text, self.style = text, style

    def __rich_console__(self, console, options):
        yield Text.from_ansi(markdown(self.text, style=self.style))


console = Console(record=True)  # /self-improve exports what the user saw
ACCENT = "#c8b4ff"
BACKGROUND = "#262626"
USER_STYLE = f"{ACCENT} on {BACKGROUND}"
MARGIN = 0
INDENT = " " * MARGIN
MAX_DIFF_LINES = 20
THOUGHT_STYLE = "dim italic"
CAUTION = "#ff9f43"  # commands and edits waiting for the user's approval

after_tools = False


def note(text: str, style: str = "dim") -> None:
    console.print(Padding.indent(Text(text, style=style), MARGIN), highlight=False)


def columns(rows: list[tuple[str, str]]) -> None:
    """Two dim columns; long text in the second column wraps under itself."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(no_wrap=True)
    grid.add_column()
    for row in rows:
        grid.add_row(*row)
    console.print(Padding.indent(grid, MARGIN + 2), style="dim")


def user(text: str) -> None:
    """Show a sent message as a full-width block, set apart from the agent's output."""
    global after_tools
    after_tools = False
    console.print()
    console.print(Padding(Text(text), (0, 1, 0, MARGIN + 1), style=USER_STYLE, expand=True))
    console.print()


def tool(name: str, detail: str) -> None:
    """One line per tool call, cut to the terminal width."""
    global after_tools
    after_tools = True
    line = Text.assemble(("● ", "cyan"), (name, "cyan"), (f"  {detail}", "dim"), no_wrap=True, overflow="ellipsis")
    console.print(Padding.indent(line, MARGIN))


def section() -> None:
    """Put a blank line between tool lines and the answer that follows them."""
    global after_tools
    if after_tools:
        console.print()
    after_tools = False


def answer(text: str) -> None:
    """Print markdown to scrollback."""
    console.print(Wrapped(text), soft_wrap=True)


def thought(text: str) -> None:
    """Print a reasoning summary to scrollback, dim and set apart by a blank line."""
    global after_tools
    console.print()
    console.print(Wrapped(text, THOUGHT_STYLE), soft_wrap=True)
    after_tools = True


def markdown(text: str, max_lines: int | None = None, style: str = "none") -> str:
    """Render markdown as indented ANSI text with no blank lines around it, keeping only the last `max_lines` lines.

    One column narrower than the space left after the margin, so full-width lines never wrap onto an extra row.
    """
    buffer = io.StringIO()
    width = console.width - MARGIN - 1
    renderer = Console(file=buffer, force_terminal=True, color_system=console.color_system, width=width)
    renderer.print(Markdown(text.strip("\n"), style=style))
    lines = buffer.getvalue().strip("\n").splitlines()
    return "\n".join(INDENT + line for line in (lines[-max_lines:] if max_lines else lines))


def diff(old: str, new: str) -> None:
    """Show removed lines in red and added lines in green, MAX_DIFF_LINES of each at most."""
    for sign, text, style in (("-", old, "red"), ("+", new, "green")):
        lines = text.splitlines()
        for line in lines[:MAX_DIFF_LINES]:
            note(f"  {sign} {line}", style=style)
        if len(lines) > MAX_DIFF_LINES:
            note(f"  {sign} … {len(lines) - MAX_DIFF_LINES} more lines")
