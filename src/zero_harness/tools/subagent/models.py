"""Which model and reasoning level a subagent runs on. The screens are in ui/pickers.py; this decides when to show
them and what their answers mean. A cancelled screen (Ctrl+C) stops the turn, as Ctrl+C does at any other prompt."""

import asyncio
import difflib

from zero_harness import config
from zero_harness.models import listing, registry, tiers
from zero_harness.ui import pickers

choosing = asyncio.Lock()  # parallel subagents ask the user once
confirmed: dict[str, tuple[str, str | None]] = {}  # exact models the user confirmed this session, by request


async def pick(model: str) -> tuple[str, str | None]:
    """The (provider/model, reasoning level) for a subagent asked to run on `model`: the fast or smart tier, the
    current model, or an exact provider/model the user confirms."""
    if model == "current":
        return config.get("model"), listing.level(config.get("model"), config.get("effort"))
    async with choosing:
        if model not in tiers.TIERS:
            return await confirm(model)
        if not tiers.saved(model)[0]:
            await setup()
    return tiers.saved(model)


async def setup() -> None:
    """First use of smart or fast: the user confirms both tiers' suggested models at once, and zero saves them."""
    chosen = await pickers.confirm_tiers({tier: await tiers.suggest(tier) for tier in tiers.TIERS})
    if chosen is None:
        raise asyncio.CancelledError
    for tier, picked in chosen.items():
        tiers.save(tier, *picked)


async def confirm(model: str) -> tuple[str, str | None]:
    """The user confirms the usable model nearest `model`, or picks another. Once per model per session."""
    if model not in confirmed:
        picked = await pickers.confirm_model(model, await closest(model))
        if picked is None:
            raise asyncio.CancelledError
        confirmed[model] = picked
    return confirmed[model]


async def closest(model: str) -> str | None:
    """The usable provider/model nearest `model`, e.g. anthropic/opus-5.5 -> anthropic/claude-opus-5-5. An exact
    match is nearest. None if the provider is unknown or has no key."""
    try:
        name, model_id = registry.split(model)
    except ValueError:
        return None
    if not registry.has_key(name):
        return None
    await registry.ensure_account(name)
    match = difflib.get_close_matches(model_id, listing.every(name), n=1, cutoff=0.4)
    return f"{name}/{match[0]}" if match else None
