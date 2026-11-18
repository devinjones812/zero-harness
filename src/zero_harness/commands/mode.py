from zero_harness import config
from zero_harness.ui.notes import note

DESCRIPTION = (
    "Approval mode. ask: ask before every command and edit. auto: review routine commands with the configured provider. "
    "auto-max: everything runs except known destructive commands. /mode <name>; /mode alone cycles."
)
MODES = OPTIONS = ["ask", "auto", "auto-max"]


def run(history: list, args: str) -> None:
    if args and args not in MODES:
        note(f"unknown mode: {args}. Use {', '.join(MODES)}.")
        return
    mode = args or MODES[(MODES.index(config.get("mode")) + 1) % len(MODES)]
    config.update("mode", mode)
    note(f"mode: {mode} (saved)")
