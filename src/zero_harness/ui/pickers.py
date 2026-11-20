"""Interactive model choice: the provider, model, and reasoning pickers, and the subagent model screens built on
them. /model and tools/subagent/models.py both use these. Every picker returns None when the user presses Ctrl+C:
questionary catches it."""

import questionary
from prompt_toolkit.application import in_terminal

from zero_harness import config, errors
from zero_harness.models import listing, registry, tiers
from zero_harness.ui import notes
from zero_harness.ui.notes import note

MORE = "more…"
USE = "use these"


def current() -> tuple[str | None, str | None]:
    """The configured (provider, model id), or Nones if there is none or its provider is gone."""
    try:
        return registry.split(config.get("model")) if config.get("model") else (None, None)
    except ValueError:
        return None, None


async def pick_provider() -> str | None:
    choices = [
        questionary.Choice(name if registry.has_key(name) else f"{name} (asks for a key)", value=name)
        for name in registry.providers()
    ]
    return await questionary.select("provider:", choices=choices, default=current()[0]).ask_async()


async def pick_configured(default: str | None = None) -> str | None:
    """Pick a provider/model from the providers that have a key, without changing the current model. `default`
    (provider/model) starts selected."""
    names = [name for name in registry.providers() if registry.has_key(name)]
    default_name, default_id = registry.split(default) if default else (None, None)
    name = (
        names[0]
        if len(names) == 1
        else await questionary.select("provider:", choices=names, default=default_name).ask_async()
    )
    if not name:
        return None
    try:
        await registry.load_account(name)
    except (ValueError, *errors.recoverable()) as error:
        note(f"{name}: could not list your models ({error}).")
        return None
    model_id = await pick_model(name, default_id if name == default_name else None)
    return f"{name}/{model_id}" if model_id else None


async def pick_model(name: str, selected: str | None = None) -> str | None:
    """The newest model of each family, with "more…" for all models, newest first. Starts on `selected`, or on the
    current model."""
    selected = selected or current()[1]
    latest = listing.latest(name)
    if latest:
        choice = await questionary.select(
            "model:", choices=[*latest, MORE], default=selected if selected in latest else None
        ).ask_async()
        if choice != MORE:
            return choice
    every = listing.every(name)
    return await questionary.select(
        "model (type to filter):",
        choices=every,
        default=selected if selected in every else None,
        use_search_filter=True,
        use_jk_keys=False,
    ).ask_async()


def default_level(model: str) -> str | None:
    """The current level if the model supports it, else medium, else its lowest. None if it doesn't reason."""
    levels = listing.efforts(model)
    if not levels:
        return None
    current_level = config.get("effort")
    return current_level if current_level in levels else "medium" if "medium" in levels else levels[0]


async def pick_level(model: str, start: str | None = None) -> str | None:
    """Ask for a reasoning level for `model`, starting on `start` if the model offers it. Returns that start if the
    user cancels, None if the model doesn't reason."""
    levels = listing.efforts(model)
    if not levels:
        return None
    start = start if start in levels else default_level(model)
    choice = await questionary.select("reasoning:", choices=levels, default=start).ask_async()
    return choice or start


async def pick_subagent(model: str | None, level: str | None) -> tuple[str, str | None] | None:
    """Pick a provider/model and reasoning level for subagents, starting on `model` and `level`. None if cancelled."""
    picked = await pick_configured(model)
    if not picked:
        return None
    return picked, await pick_level(picked, level)


async def confirm_tiers(chosen: dict[str, tuple[str, str | None]]) -> dict[str, tuple[str, str | None]] | None:
    """The first-use screen: show each subagent tier's suggested model, and let the user change any. Returns the
    choices, or None on Ctrl+C."""
    note("zero wants a subagent. Confirm the models for smart and fast subagents; zero saves them.", notes.CAUTION)
    note("Change them later with /model smart or /model fast.", notes.CAUTION)
    while True:
        for tier, picked in chosen.items():
            note(f"  {tier:<6} {' '.join(filter(None, picked))}  ({tiers.TIERS[tier]['use']})", notes.CAUTION)
        async with in_terminal():  # pauses zero's input box so the picker can use the terminal
            choice = await questionary.select(
                "subagent models:", choices=[USE, *(f"change {tier}" for tier in chosen)]
            ).ask_async()
            if choice is None:
                return None
            if choice == USE:
                return chosen
            tier = choice.removeprefix("change ")
            chosen[tier] = await pick_subagent(*chosen[tier]) or chosen[tier]


async def confirm_model(requested: str, start: str | None) -> tuple[str, str | None] | None:
    """The screen for a subagent on a model the user named: the picker opens on `start`. None on Ctrl+C."""
    note(f"zero wants a subagent on {requested}. Confirm it, or pick another model.", notes.CAUTION)
    async with in_terminal():
        return await pick_subagent(start, config.get("effort"))
