from rich.style import Style
from rich.text import Text

from zero_harness.ui.notes import console

START = "#7ef0ff"
END = "#3a7bff"
SHADE = 0.5
BOLT = ("⚡︎", "bold #e0e0e0")
TAG = ("ʙᴜɪʟᴛʙʏᴅᴇᴠɪɴ", "bold #e0e0e0")

# 7x8 pixel letters, drawn 2 pixels per character with half blocks, so 4 lines tall.
LETTERS = {
    "z": ["#######", "#######", "....###", "...###.", ".###...", "###....", "#######", "#######"],
    "e": ["#######", "#######", "###....", "######.", "######.", "###....", "#######", "#######"],
    "r": ["######.", "#######", "###..##", "#######", "######.", "###.###", "###..##", "###..##"],
    "o": [".#####.", "#######", "###.###", "###.###", "###.###", "###.###", "#######", ".#####."],
}


def blend(start: str, end: str, t: float) -> str:
    """Mix two hex colors; t=0 gives start, t=1 gives end."""
    a = [int(start[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(end[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def zero() -> list[Text]:
    """'zero' in pixel letters with a left-to-right gradient and a drop shadow."""
    rows = ["..".join(LETTERS[c][r] for c in "zero") for r in range(8)]
    width = len(rows[0]) + 1
    face = lambda c: blend(START, END, c / (width - 1))
    pixels = [[None] * width for _ in range(8)]
    for r, row in enumerate(rows[:-1]):
        for c, ch in enumerate(row):
            if ch == "#":
                pixels[r + 1][c + 1] = blend(face(c + 1), "#000000", SHADE)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                pixels[r][c] = face(c)
    lines = []
    for top_row, bottom_row in zip(pixels[::2], pixels[1::2]):
        line = Text()
        for top, bottom in zip(top_row, bottom_row):
            if top:
                line.append("▀", Style(color=top, bgcolor=bottom))
            elif bottom:
                line.append("▄", Style(color=bottom))
            else:
                line.append(" ")
        lines.append(line)
    return lines


def show() -> None:
    """Print the logo, or a one-line version when the terminal is too narrow."""
    lines = zero()
    console.print()
    if console.width <= lines[0].cell_len + 16:
        console.print(Text.assemble(("zero ", f"bold {START}"), BOLT, TAG))
    else:
        lines[-1].append_text(Text.assemble("  ", BOLT, TAG))
        console.print(Text("\n").join(lines), no_wrap=True)
    console.print()
