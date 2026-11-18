import re

from zero_harness import config

# Standard tier, USD per 1M tokens: (input, cached input, output). OpenAI pricing page, Nov 2026.
PRICES = {
    "gpt-6.2-astra": (8.00, 0.40, 40.00),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
    "gpt-6.1-terra": (1.00, 0.05, 5.00),
    "gpt-6-astra": (10.00, 1.00, 50.00),
    "gpt-6-sol": (2.00, 0.20, 10.00),
    "gpt-6-luna": (0.10, 0.01, 0.50),
}
CONTEXT_WINDOW = 1_050_000
LONG_CONTEXT = 272_000
WHEEL = "○◔◑◕●"

cost = 0.0
priced = True
input_tokens = 0


def record(response, conversation: bool = True) -> None:
    """Add a response's cost to the session. Conversation calls also set the current context size."""
    global cost, priced, input_tokens
    usage, model = response.usage, response.model
    if conversation:
        input_tokens = usage.input_tokens
    price = PRICES.get(re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model))
    if price is None:
        priced = False
        return
    long = usage.input_tokens > LONG_CONTEXT
    cached = usage.input_tokens_details.cached_tokens
    cost += (
        (usage.input_tokens - cached) * price[0] * (2 if long else 1)
        + cached * price[1] * (2 if long else 1)
        + usage.output_tokens * price[2] * (1.5 if long else 1)
    ) / 1_000_000


def status() -> str:
    """One line: context wheel and percent, tokens, session cost, model and effort, auto mode."""
    used = input_tokens / CONTEXT_WINDOW
    wheel = WHEEL[min(round(used * 4), 4)]
    price = f"${cost:.2f}" if priced else f"${cost:.2f}+ (unknown price for {config.get('model')})"
    auto = "  auto" if config.get("auto") else ""
    tokens = f"{input_tokens / 1000:.1f}k" if input_tokens >= 1000 else str(input_tokens)
    return f" {wheel} {used:.0%} context  {tokens}/1M  {price}  {config.get('model')} {config.get('effort')}{auto}"
