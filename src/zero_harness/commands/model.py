import os

from zero_harness import config, errors
from zero_harness.models import listing, registry, tiers
from zero_harness.ui import pickers, user_input
from zero_harness.ui.notes import note

DESCRIPTION = "switch model, or the smart or fast subagent model"


def complete(words: list[str]) -> list[str]:
    """Providers and subagent tiers, then the provider's newest model of each family."""
    if not words:
        return [*registry.providers(), *tiers.TIERS]
    if len(words) == 1 and words[0] in registry.providers():
        return listing.latest(words[0])
    return []


async def run(history: list, args: str) -> None:
    words = args.split()
    if words and words[0] in tiers.TIERS:
        await set_tier(words[0])
        return
    name = words[0] if words else await pickers.pick_provider()
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
    except (ValueError, *errors.recoverable()) as error:
        note(f"{name}: could not list your models ({error}).")
        if getattr(error, "status_code", None) != 401 or not await ask_key(name):
            return
        try:
            await registry.load_account(name)
        except (ValueError, *errors.recoverable()) as error:
            note(f"{name}: could not list your models ({error}).")
            return
    if len(words) > 1 and words[1] not in registry.account[name]:
        note(f"{name} has no model {words[1]!r} for your key. Try /model {name} for a list.")
        return
    model_id = words[1] if len(words) > 1 else await pickers.pick_model(name)
    if not model_id:
        return
    model = f"{name}/{model_id}"
    level = await pickers.pick_level(model)
    config.update("model", model)
    if level:
        config.update("effort", level)
    note(f"model: {model}{f' {level}' if level else ''} (saved)")


async def set_tier(tier: str) -> None:
    """/model smart or /model fast: pick the tier's model and reasoning level, starting on the saved or suggested."""
    model, level = tiers.saved(tier)
    if not model:
        model, level = await tiers.suggest(tier)
    picked = await pickers.pick_subagent(model, level)
    if picked:
        tiers.save(tier, *picked)
        note(f"{tier} subagents: {' '.join(filter(None, picked))} (saved)")


async def ask_key(name: str) -> bool:
    """Ask for a provider's API key without showing it, and save it to ~/.zero/.env. False if none entered."""
    settings = registry.provider(name)
    env = settings["key_env"]
    note(f"{name} needs {env}.", style="default")
    if "key_url" in settings:
        note(f"Create one at {settings['key_url']}")
    key = await user_input.secret("Paste key: ")
    key = (key or "").strip().removeprefix(f"{env}=").strip()
    if not key:
        return False
    config.HOME.mkdir(parents=True, exist_ok=True)
    env_file = config.HOME / ".env"
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    lines = [line for line in lines if not line.startswith(f"{env}=")]
    env_file.write_text("\n".join([*lines, f"{env}={key}"]) + "\n")
    env_file.chmod(0o600)
    os.environ[env] = key
    return True
