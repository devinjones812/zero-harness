"""Subagent tiers: the model and reasoning level that "smart" and "fast" subagents run on."""

from zero_harness import config
from zero_harness.models import listing, registry

# Preferred families by provider. The catalog supplies each family's newest model, so releases need no code change.
# Providers not listed, or whose family is gone, go by price.
TIERS = {
    "smart": {
        "use": "hard, narrow problems",
        "effort": "medium",
        "families": {"openai": "gpt-astra", "anthropic": "claude-fable"},
        "by_price": listing.smartest,
    },
    "fast": {
        "use": "simple searches",
        "effort": "low",
        "families": {"openai": "gpt-sol", "anthropic": "claude-sonnet"},
        "by_price": listing.cheapest,
    },
}


def saved(tier: str) -> tuple[str | None, str | None]:
    """The tier's saved (provider/model, reasoning level). Model is None until the user confirms one."""
    return config.get(f"{tier}_model"), config.get(f"{tier}_effort")


def save(tier: str, model: str, level: str | None) -> None:
    config.update(f"{tier}_model", model)
    config.update(f"{tier}_effort", level)


async def suggest(tier: str) -> tuple[str, str | None]:
    """The tier's family on the current provider, else by price; then the same on other providers with a key.
    Falls back to the current model."""
    current, _ = registry.split(config.get("model"))
    for name in dict.fromkeys([current, *registry.providers()]):
        if not registry.has_key(name):
            continue
        await registry.ensure_account(name)
        family = TIERS[tier]["families"].get(name)
        if found := (family and listing.newest(name, family)) or TIERS[tier]["by_price"](name):
            model = f"{name}/{found}"
            return model, listing.level(model, TIERS[tier]["effort"])
    return config.get("model"), listing.level(config.get("model"), config.get("effort"))
