import re

import questionary

from zero_harness import config, llm
from zero_harness.commands.effort import LEVELS
from zero_harness.ui.notes import note

DESCRIPTION = "Switch models. /model picks a model, then its effort; /model <id> switches directly."

CHAT_MODEL = re.compile(r"^gpt-([6-9]|\d{2,})(\.\d+)?(-[a-z]+)?$")


async def chat_models() -> list[str]:
    """Return the key's GPT-6 and newer chat models, newest first. Hides dated, audio, image, and realtime models."""
    ids = [m.id async for m in llm.client.models.list() if CHAT_MODEL.match(m.id)]
    return sorted(ids, reverse=True)


async def run(history: list, args: str) -> None:
    choice = args
    if not choice:
        models = await chat_models()
        current = config.get("model")
        default = current if current in models else None
        choice = await questionary.select("model:", choices=models, default=default).ask_async()
        if not choice:
            return
        level = await questionary.select("effort:", choices=LEVELS, default=config.get("effort")).ask_async()
        if level:
            config.update("effort", level)
    if choice:
        config.update("model", choice)
        note(f"model: {choice} {config.get('effort')} (saved)")
