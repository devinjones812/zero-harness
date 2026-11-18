import os

import questionary

from zero_harness import config, errors
from zero_harness.commands import reasoning
from zero_harness.models import listing, registry
from zero_harness.ui.notes import note

DESCRIPTION = "Switch models: /model picks a provider, model, and reasoning. /model <provider> <model> skips ahead."
MORE = "more…"


def complete(words: list[str]) -> list[str]:
    """Providers, then the provider's newest model of each family."""
    if not words:
        return list(registry.providers())
    if len(words) == 1 and words[0] in registry.providers():
        return listing.latest(words[0])
    return []


async def run(history: list, args: str) -> None:
    words = args.split()
    name = words[0] if words else await pick_provider()
    if not name:
        return
    if name not in registry.providers():
        note(f"unknown provider {name!r}. Use one of: {', '.join(registry.providers())}. Ask zero to add others.")
        return
    if not registry.has_key(name) and not await ask_key(name):
        note(f"no key entered for {name}.")
        return
    try:
        await registry.load_account(name)
    except (ValueError, *errors.RECOVERABLE) as error:
        note(f"{name}: could not list your models ({error}).")
        return
    if len(words) > 1 and words[1] not in registry.account[name]:
        note(f"{name} has no model {words[1]!r} for your key. Try /model {name} for a list.")
        return
    model_id = words[1] if len(words) > 1 else await pick_model(name)
    if not model_id:
        return
    model = f"{name}/{model_id}"
    level = await reasoning.pick(model)
    config.update("model", model)
    if level:
        config.update("effort", level)
    note(f"model: {model}{f' {level}' if level else ''} (saved)")


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


async def pick_model(name: str) -> str | None:
    """The newest model of each family, with "more…" for all models, newest first."""
    selected = current()[1]
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


async def ask_key(name: str) -> bool:
    """Ask for a provider's API key without showing it, and save it to ~/.zero/.env. False if none entered."""
    settings = registry.provider(name)
    env = settings["key_env"]
    where = f" Create one at {settings['key_url']}" if "key_url" in settings else ""
    key = await questionary.password(f"{name} needs {env}.{where}\n  Paste it:").ask_async()
    if not key or not key.strip():
        return False
    config.HOME.mkdir(parents=True, exist_ok=True)
    env_file = config.HOME / ".env"
    with env_file.open("a") as file:
        file.write(f"\n{env}={key.strip()}\n")
    env_file.chmod(0o600)
    os.environ[env] = key.strip()
    return True
