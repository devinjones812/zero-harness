import os

from zero_harness import config
from zero_harness.models import registry
from zero_harness.web import anthropic, openai, parallel

NATIVE = {"openai": openai, "anthropic": anthropic}
NOT_CONFIGURED = (
    "No web search provider is configured for {model}. Tell the user: web search works with OpenAI and "
    "Anthropic models. For other models, add a Parallel key (recommended: https://parallel.ai) as "
    "PARALLEL_API_KEY in ~/.zero/.env, then /reload."
)


def choose():
    """Parallel if the user chose it, else the chat model's provider's own search, else Parallel if its key is set.

    Raises with a message for the model when there is none.
    """
    has_parallel = bool(os.getenv("PARALLEL_API_KEY"))
    if config.saved.get("search_provider") == "parallel" and has_parallel:
        return parallel
    name = registry.split(config.get("model"))[0]
    if name in NATIVE:
        return NATIVE[name]
    if has_parallel:
        return parallel
    raise RuntimeError(NOT_CONFIGURED.format(model=config.get("model")))
