"""What models.dev and the user's account say about models: which to list, prices, context sizes, reasoning levels."""

from datetime import date, timedelta

from zero_harness import catalog
from zero_harness.models import registry

# Reasoning levels for models that reason but whose levels models.dev doesn't list.
EFFORTS = ["low", "medium", "high", "xhigh", "max"]
# /model's short list shows only families with a release in this many days.
CURRENT_DAYS = 183


def known(name: str) -> dict:
    """models.dev's entries for a provider's agentic models (tool calls, text answers), or {} if it doesn't list it.

    Once registry.load_account() has run, only models the key can use: models.dev also lists restricted models.
    """
    entries = catalog.providers.get(registry.provider(name).get("catalog", name), {})
    usable = registry.account.get(name)
    return {
        model_id: entry
        for model_id, entry in entries.items()
        if entry["agentic"] and (usable is None or model_id in usable)
    }


def latest(name: str) -> list[str]:
    """The newest model of each current family (e.g. one Opus, one Sonnet), newest first.

    Hides families with no release in CURRENT_DAYS. Empty if models.dev doesn't list the provider.
    """
    newest = {}
    for model_id, entry in known(name).items():
        current = newest.get(entry["family"])
        if current is None or entry["released"] > current[1]["released"]:
            newest[entry["family"]] = (model_id, entry)
    ordered = sorted(newest.values(), key=lambda pair: pair[1]["released"], reverse=True)
    cutoff = (date.today() - timedelta(days=CURRENT_DAYS)).isoformat()
    recent = [model_id for model_id, entry in ordered if entry["released"] >= cutoff]
    # A provider with nothing recent still shows its newest families.
    return recent or [model_id for model_id, _ in ordered]


def every(name: str) -> list[str]:
    """All of a provider's usable agentic models, newest first. Needs registry.load_account() first.

    If models.dev doesn't list the provider: every model the key can use, by name.
    """
    entries = known(name)
    if entries:
        return sorted(entries, key=lambda model_id: entries[model_id]["released"], reverse=True)
    return sorted(registry.account.get(name, []))


def info(model: str) -> dict:
    """A model's models.dev entry: "cost" (USD per 1M tokens), "context" (tokens), and more. {} if unknown."""
    name, model_id = registry.split(model)
    return catalog.model(registry.provider(name).get("catalog", name), model_id)


def efforts(model: str) -> list[str]:
    """The model's reasoning levels. Empty if it doesn't reason."""
    levels = info(model).get("efforts")
    return EFFORTS if levels is None else levels


def cheapest(name: str) -> str | None:
    """The provider's cheapest current model, for side jobs like web search. None if prices are unknown."""
    entries = known(name)
    priced = [model_id for model_id in latest(name) if entries[model_id]["cost"]]
    return min(priced, key=lambda model_id: entries[model_id]["cost"]["input"], default=None)


def smartest(name: str) -> str | None:
    """The provider's most capable current model, taken to be its most expensive. None if prices are unknown."""
    entries = known(name)
    priced = [model_id for model_id in latest(name) if entries[model_id]["cost"]]
    return max(priced, key=lambda model_id: entries[model_id]["cost"]["output"], default=None)
