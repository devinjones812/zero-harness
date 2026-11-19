import asyncio
import os
import re
import time
from bisect import bisect_left

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
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

RESIZE_SETTLE = 0.15  # seconds after the last resize before the screen is rebuilt
MAX_REPRINT_LINES = 2000
CUT_NOTE = "(earlier output is hidden after a resize; /history shows all of it)"

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
    """A /command is one line. A first word with another slash is a path, e.g. a dragged-in image."""
    return text.startswith("/") and "\n" not in text and "/" not in text.split(" ", 1)[0][1:]


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


class CharacterCount(Processor):
    """Show how many characters were typed instead of the text, so a pasted key stays hidden and on one row."""

    def apply_transformation(self, ti):
        size = len(fragment_list_to_text(ti.fragments))
        shown = f"{size} characters" if size else ""
        return Transformation([("", shown)], lambda i: len(shown), lambda i: size)


async def secret(message: str) -> str | None:
    """Ask for a secret such as an API key. None if the user cancels."""
    try:
        return await PromptSession().prompt_async(message, input_processors=[CharacterCount()])
    except KeyboardInterrupt, EOFError:
        return None


class CommandCompleter(Completer):
    """Complete /command names, then each word after them with the command's complete(words)."""

    def __init__(self, commands: dict):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not is_command(text):
            return
        name, space, rest = text[1:].partition(" ")
        if not space:
            words, typed = [f"/{name}" for name in self.commands], text
        elif name in self.commands:
            *before, typed = rest.split(" ")
            words = self.commands[name](before)
        else:
            return
        for word in words:
            if word.startswith(typed):
                yield Completion(word, start_position=-len(typed))


def setup(busy, commands: dict) -> None:
    """Create the prompt, pinned to the bottom of the terminal. Top to bottom:

    the answer being streamed (right under earlier output, so it reads top to bottom and finished blocks
    land where they streamed), empty space, one blank row that stays when the screen is full,
    working… and the stats, a rule, the input, a rule.

    `commands` maps each /command name to complete(words), for Tab completion.
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

    timer, built_for = None, None

    def schedule_rebuild() -> None:
        """A window drag sends many resizes. Rebuild once, after the last one."""
        nonlocal timer
        if timer:
            timer.cancel()
        timer = asyncio.get_running_loop().call_later(RESIZE_SETTLE, rebuild)

    def rebuild() -> None:
        """Clear the screen and scrollback, reprint the conversation at the new width, and redraw the box.

        A terminal rewraps printed rows when it resizes, and how is up to the terminal, so a redraw in place
        can't know where the old box went and leaves copies.
        """
        nonlocal built_for
        app = session.app
        # prompt_toolkit also polls the size, so one resize can arrive twice.
        if not app.is_running or app.output.get_size() == built_for:
            return
        built_for = app.output.get_size()
        lines = notes.console.printed_lines(MAX_REPRINT_LINES)
        if len(lines) > MAX_REPRINT_LINES:
            lines = [f"\x1b[2m{CUT_NOTE}\x1b[0m", *lines[-MAX_REPRINT_LINES:]]
        # Synchronized output (?2026) shows the clear and the reprint as one frame on terminals that support it.
        app.output.write_raw(
            "\x1b[?2026h\x1b[H\x1b[2J\x1b[3J" + "".join(f"{line}\r\n" for line in lines) + "\x1b[?2026l"
        )
        app.output.flush()
        app.renderer.reset(leave_alternate_screen=False)
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
        completer=CommandCompleter(commands),
        style=STYLE,
        erase_when_done=True,
        tempfile_suffix=".md",
        refresh_interval=0.3,
        reserve_space_for_menu=0,
        color_depth=ColorDepth.TRUE_COLOR if os.environ.get("COLORTERM") in ("truecolor", "24bit") else None,
    )
    # prompt_toolkit has no public resize hook; it reads this attribute when the prompt starts.
    session.app._on_resize = schedule_rebuild
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
