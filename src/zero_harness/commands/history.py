import subprocess

from prompt_toolkit.application import run_in_terminal

from zero_harness.ui import notes

DESCRIPTION = "view full output"
ANYTIME = True


def page(text: str) -> None:
    # less: -R keeps colors, +G opens at the end.
    subprocess.run(["less", "-R", "+G"], check=False, input=text, text=True)


async def run(history: list, args: str) -> None:
    text = "".join(f"{line}\n" for line in notes.console.printed_lines())
    await run_in_terminal(lambda: page(text), in_executor=True)
