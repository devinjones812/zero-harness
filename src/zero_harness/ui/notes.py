import io

from rich.console import Console
from rich.markdown import Markdown
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

console = Console(record=True)  # /self-improve exports what the user saw

ACCENT = "#c8b4ff"
BACKGROUND = "#262626"
USER_STYLE = f"{ACCENT} on {BACKGROUND}"
MARGIN = 0
INDENT = " " * MARGIN
MAX_DIFF_LINES = 20

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
    console.print(Text.from_ansi(markdown(text)), soft_wrap=True)


def markdown(text: str, max_lines: int | None = None) -> str:
    """Render markdown as indented ANSI text with no blank lines around it, keeping only the last `max_lines` lines.

    One column narrower than the space left after the margin, so full-width lines never wrap onto an extra row.
    """
    buffer = io.StringIO()
    width = console.width - MARGIN - 1
    renderer = Console(file=buffer, force_terminal=True, color_system=console.color_system, width=width)
    renderer.print(Markdown(text.strip("\n")))
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
