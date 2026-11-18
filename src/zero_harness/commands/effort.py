from zero_harness import config
from zero_harness.ui.notes import note

DESCRIPTION = "Set reasoning effort: /effort low|medium|high|xhigh|max (saved)."

LEVELS = ["low", "medium", "high", "xhigh", "max"]


def run(history: list, args: str) -> None:
    if args in LEVELS:
        config.update("effort", args)
    elif args:
        note(f"unknown effort {args!r}. Use one of: {', '.join(LEVELS)}")
        return
    note(f"reasoning effort: {config.get('effort')}")
