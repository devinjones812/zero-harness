import questionary

from zero_harness import config
from zero_harness.ui.notes import note

DESCRIPTION = "set approval mode"
MODES = OPTIONS = ["ask", "auto-review", "auto-max"]
NEEDS_REVIEWER = "needs an OpenAI or TypeSafe key"
NO_REVIEWER = (
    "auto-review needs a reviewer: add OPENAI_API_KEY (OpenAI Decisions) or TYPESAFE_API_KEY (Jev) "
    f"to {config.HOME / '.env'}. Until then, use ask or auto-max."
)


async def run(history: list, args: str) -> None:
    if args and args not in MODES:
        note(f"unknown mode: {args}. Use {', '.join(MODES)}.")
        return
    if args == "auto-review" and not config.reviewer():
        note(NO_REVIEWER)
        return
    mode = args or await pick()
    if not mode:
        return
    config.update("mode", mode)
    note(f"mode: {mode} (saved)")


async def pick() -> str | None:
    """A menu of modes. Without a reviewer, auto-review shows grayed out with the reason."""
    disabled = None if config.reviewer() else NEEDS_REVIEWER
    choices = [questionary.Choice(mode, disabled=disabled if mode == "auto-review" else None) for mode in MODES]
    current = config.get("mode")
    default = current if current in MODES and not (current == "auto-review" and disabled) else None
    return await questionary.select("mode:", choices=choices, default=default).ask_async()
