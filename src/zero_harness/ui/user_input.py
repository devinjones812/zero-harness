import asyncio
import os
import re
import time
from bisect import bisect_left

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.filters import Condition, to_filter
from prompt_toolkit.formatted_text import ANSI, fragment_list_to_text
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import get_cwidth

from zero_harness import sessions, usage
from zero_harness.ui import notes

STYLE = Style.from_dict(
    {
        "input": f"bg:{notes.BACKGROUND}",
        "prompt": f"{notes.ACCENT} bold",
        "question": "ansiyellow bold",
        "status": "#808080",
        "rule": "#4a4a4a",
    }
)

session: PromptSession | None = None
live = ""
live_style = "none"
question = ""
answer_future: asyncio.Future | None = None

bindings = KeyBindings()


@bindings.add("enter")
def submit_or_newline(event) -> None:
    """Enter sends. A trailing backslash turns Enter into a newline."""
    buffer = event.current_buffer
    if buffer.document.text_before_cursor.endswith("\\"):
        buffer.delete_before_cursor(1)
        buffer.insert_text("\n")
    else:
        buffer.validate_and_handle()


@bindings.add("escape", "enter")
def newline(event) -> None:
    event.current_buffer.insert_text("\n")


@bindings.add("c-e")
def edit_in_editor(event) -> None:
    """Ctrl+E opens the input in $EDITOR. Save and quit to put the text back in the input."""
    event.current_buffer.open_in_editor()


@bindings.add("c-c")
def clear_or_interrupt(event) -> None:
    """Ctrl+C clears typed text. With nothing typed, it stops the agent or quits."""
    if event.current_buffer.text:
        event.current_buffer.reset()
    else:
        event.app.exit(exception=KeyboardInterrupt())


def is_command(text: str) -> bool:
    return text.startswith("/") and "\n" not in text


class WordWrap(Processor):
    """Wrap the input between words. prompt_toolkit wraps mid-word, so pad the row when the next word won't fit."""

    def __init__(self, prompt):
        self.prompt = prompt

    def apply_transformation(self, ti):
        chars = explode_text_fragments(ti.fragments)
        text = fragment_list_to_text(chars)
        # Only the first row has the prompt in front of it.
        column = get_cwidth(fragment_list_to_text(self.prompt())) if ti.lineno == 0 else 0
        out, positions, display = [], [], 0  # positions[i]: where source character i lands on screen
        for word in re.finditer(r"\S+|\s+", text):
            size = get_cwidth(word.group())
            if column and not word.group().isspace() and column + size > ti.width >= size:
                out.append(("", " " * (ti.width - column)))
                display += ti.width - column
                column = 0
            for i in range(word.start(), word.end()):
                char_width = get_cwidth(text[i])
                column = (0 if column + char_width > ti.width else column) + char_width
                column %= ti.width
                positions.append(display)
                out.append(chars[i])
                display += 1
        positions.append(display)
        return Transformation(out, lambda i: positions[min(i, len(text))], lambda i: bisect_left(positions, i))


def setup(busy, commands: list[str]) -> None:
    """Create the prompt, pinned to the bottom of the terminal. Top to bottom:

    the answer being streamed (right under earlier output, so it reads top to bottom and finished blocks
    land where they streamed), empty space, one blank row that stays when the screen is full,
    working… and the stats, a rule, the input, a rule.
    """
    global session

    def streamed():
        rows = session.app.output.get_size().rows - 9
        return ANSI(notes.markdown(live, max_lines=rows, style=live_style))

    def status_line():
        dots = "." * (int(time.monotonic() * 3) % 3 + 1)
        working = f"{notes.INDENT}working{dots}" if busy() and not question else ""
        stats = usage.status().strip()
        width = session.app.output.get_size().columns - 1
        gap = max(width - len(working) - len(stats), 2)
        return [("class:status", f"{working}{' ' * gap}{stats}"[:width])]

    def redraw_on_resize() -> None:
        """Erase the box and redraw it. Output above the box stays. When the terminal narrows, it rewraps each
        drawn row longer than the new width onto more rows, so count those rows to find the top of the box."""
        app, renderer = session.app, session.app.renderer
        drawn, cursor = renderer._last_screen, renderer._cursor_pos
        columns = app.output.get_size().columns
        up = cursor.y
        if drawn and renderer._last_size and columns < renderer._last_size.columns:
            up = cursor.x // columns
            for y in range(cursor.y):
                row = drawn.data_buffer[y]
                length = max((x + 1 for x, char in row.items() if char.char != " "), default=0)
                up += max(1, -(-length // columns))
        app.output.cursor_up(up)
        app.output.write_raw("\r")
        app.output.erase_down()
        app.output.flush()
        renderer.reset(leave_alternate_screen=False)
        # The renderer fills the rows below the cursor; this measures them again.
        app._request_absolute_cursor_position()
        app.invalidate()

    def prompt():
        if question:
            return [("class:question", f"{notes.INDENT}{question} ")]
        return [("class:prompt", f"{notes.INDENT}❯ ")]

    sessions.DIR.mkdir(exist_ok=True)
    session = PromptSession(
        prompt,
        history=FileHistory(str(sessions.DIR / "prompt_history")),
        key_bindings=bindings,
        input_processors=[WordWrap(prompt)],
        completer=WordCompleter([f"/{name}" for name in commands], sentence=True),
        style=STYLE,
        erase_when_done=True,
        tempfile_suffix=".md",
        refresh_interval=0.3,
        reserve_space_for_menu=0,
        color_depth=ColorDepth.TRUE_COLOR if os.environ.get("COLORTERM") in ("truecolor", "24bit") else None,
    )
    # prompt_toolkit has no public resize hook; it reads this attribute when the prompt starts.
    session.app._on_resize = redraw_on_resize
    input_window = session.app.layout.current_window
    input_window.style = "class:input"
    # Only the empty space at the top may stretch; that is what pins the box to the bottom of the terminal.
    input_window.dont_extend_height = to_filter(True)
    rule = Window(char="─", height=1, style="class:rule")
    screen = HSplit(
        [
            ConditionalContainer(
                Window(FormattedTextControl(streamed), dont_extend_height=True),
                filter=Condition(lambda: bool(live.strip())),
            ),
            Window(),
            Window(height=1),
            Window(FormattedTextControl(status_line), height=1),
            rule,
            session.app.layout.container,
            rule,
        ]
    )
    # The completion menu floats over the whole screen; inside the one-row input it has no room to open.
    menu = Float(xcursor=True, ycursor=True, content=CompletionsMenu(max_height=8, scroll_offset=1))
    session.app.layout = Layout(FloatContainer(screen, [menu]), focused_element=input_window)


async def read() -> str:
    """Wait for the next non-empty line the user sends."""
    while True:
        text = (await session.prompt_async()).strip("\n")
        if text.strip():
            return text


def show_live(text: str, style: str = "none") -> None:
    global live, live_style
    live, live_style = text, style
    session.app.invalidate()


async def ask(text: str) -> str:
    """Show `text` as the prompt and wait for the user's answer."""
    global question, answer_future
    question, answer_future = text, asyncio.get_running_loop().create_future()
    session.app.invalidate()
    try:
        return await answer_future
    finally:
        question, answer_future = "", None
        session.app.invalidate()


def answer(text: str) -> bool:
    """If a question is waiting, answer it with `text` and return True."""
    if answer_future is None or answer_future.done():
        return False
    notes.note(f"  ↳ {text}")
    answer_future.set_result(text)
    return True
