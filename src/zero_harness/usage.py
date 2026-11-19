from zero_harness import config
from zero_harness.models import listing
from zero_harness.models.reply import Reply, Usage

WHEEL = "○◔◑◕●"

cost = 0.0
priced = True
input_tokens: int | None = 0


def record(reply: Reply, conversation: bool = True, model: str | None = None) -> float:
    """Add a reply's cost to the session, priced for `model` or the configured model, and return it. Conversation
    calls also set the current context size."""
    global cost, priced, input_tokens
    if conversation:
        input_tokens = reply.usage.input_tokens
    rates = listing.info(model or config.get("model")).get("cost")
    if rates is None:
        priced = False
        return 0.0
    spent = dollars(reply.usage, rates)
    cost += spent
    return spent


def dollars(usage: Usage, rates: dict) -> float:
    """The cost of one call. `rates` is a models.dev cost entry: USD per 1M tokens, with optional tiers."""
    # A tier replaces the base rates for requests with more input than its size, e.g. long-context pricing.
    for tier in rates.get("tiers", []):
        if tier["tier"]["type"] == "context" and usage.input_tokens > tier["tier"]["size"]:
            rates = rates | tier
    read = rates.get("cache_read", rates["input"])
    write = rates.get("cache_write", rates["input"])
    uncached = usage.input_tokens - usage.cached_tokens - usage.cache_write_tokens
    return (
        uncached * rates["input"]
        + usage.cached_tokens * read
        + usage.cache_write_tokens * write
        # Output tokens include reasoning tokens.
        + usage.output_tokens * rates["output"]
    ) / 1_000_000


def status() -> str:
    """One line: context wheel and percent, tokens, session cost, model and reasoning, approval mode."""
    model = config.get("model")
    window = listing.info(model).get("context")
    if input_tokens is None:
        context = "○ context unmeasured"
    elif window is None:
        context = f"{short(input_tokens)} context"
    else:
        used = input_tokens / window
        wheel = WHEEL[min(round(used * 4), 4)]
        context = f"{wheel} {used:.0%} context  {short(input_tokens)}/{short(window)}"
    price = f"${cost:.2f}" if priced else f"${cost:.2f}+ (unknown price for {model})"
    reasoning = f" {config.get('effort')}" if listing.efforts(model) else ""
    auto = "" if config.get("mode") == "ask" else f"  {config.get('mode')}"
    return f" {context}  {price}  {model}{reasoning}{auto}"


def short(tokens: int) -> str:
    """1234 -> 1.2k, 1000000 -> 1M."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.3g}M"
    return f"{tokens / 1000:.1f}k" if tokens >= 1000 else str(tokens)
