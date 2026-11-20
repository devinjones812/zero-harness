"""Model providers. OpenAI and Anthropic are built in. Others go under "providers" in ~/.zero/config.json:

  "providers": {
    "<name>": {"api": "responses", "base_url": "https://example.com/v1", "key_env": "EXAMPLE_API_KEY"}
  }

- "api" names a module in APIS. Default "responses" (OpenAI's Responses API, which many providers serve).
- "base_url" defaults to the API's own. "key_env" names the key in ~/.zero/.env.
- "catalog" is the provider's id on models.dev, if it differs from <name>. models.dev supplies model lists,
  prices, context sizes, and reasoning levels (see listing.py).
Models are "<name>/<model id>"; /model lists them.

To support a new API, add a module with client(), list_models(), and call() that returns a Reply,
converting history (Responses-API items) on the way in and the reply back to items on the way out."""

import asyncio
import os
import random
from functools import cache

from zero_harness import config, errors
from zero_harness.models import anthropic, responses
from zero_harness.models.reply import Reply

SLOT_WAIT = 120  # seconds a call waits for a free request slot
APIS = {"responses": responses, "anthropic": anthropic}
BUILT_IN = {
    "openai": {"api": "responses", "key_env": "OPENAI_API_KEY", "key_url": "https://platform.openai.com/api-keys"},
    "anthropic": {
        "api": "anthropic",
        "key_env": "ANTHROPIC_API_KEY",
        "key_url": "https://platform.claude.com/settings/keys",
    },
}

# Model ids each provider's key can use, from load_account().
account: dict[str, set[str]] = {}


def providers() -> dict:
    return BUILT_IN | config.get("providers")


def split(model: str) -> tuple[str, str]:
    """Return (provider name, provider's model id). Ids without a "/" are OpenAI's, as older configs saved them."""
    name, slash, model_id = model.partition("/")
    if not slash:
        return "openai", model
    if name not in providers():
        raise ValueError(f"model {model!r} names an unknown provider {name!r}. Pick a model with /model.")
    return name, model_id


def provider(name: str) -> dict:
    return providers()[name]


def api(name: str):
    kind = provider(name).get("api", "responses")
    if kind not in APIS:
        raise ValueError(f'provider {name}: "api" must be one of {", ".join(APIS)}, not {kind!r}.')
    return APIS[kind]


def has_key(name: str) -> bool:
    return bool(os.getenv(provider(name)["key_env"]))


def client(name: str):
    settings = provider(name)
    key = os.getenv(settings["key_env"])
    if not key:
        raise ValueError(f"Set {settings['key_env']} in {config.HOME / '.env'} to use {name} models.")
    return _client(api(name), settings.get("base_url"), key)


@cache
def _client(module, base_url: str | None, key: str):
    """One client per API, URL, and key, so a changed key gets a new client."""
    return module.client(base_url, key)


async def call(*, instructions, history, tools=(), effort=None, tool_choice=None, live=None, model=None) -> Reply:
    """Send history to `model`, or the configured model. `live` shows the reply as it streams; None means no display.

    Anthropic limits how many requests an account has open at once, without saying how many. When zero's own calls
    (the main agent and subagents) exceed it, wait for one to finish and retry, up to SLOT_WAIT seconds.
    """
    name, model_id = split(model or config.get("model"))
    waited = 0.0
    while True:
        try:
            return await api(name).call(
                client(name),
                model_id,
                instructions=instructions,
                history=history,
                tools=list(tools),
                effort=effort,
                tool_choice=tool_choice,
                live=live,
            )
        except Exception as error:
            if type(error).__name__ != "RateLimitError":  # the same name in both SDKs
                raise
            if "concurrent connections" not in str(error):
                raise errors.RateLimited(
                    f"{name} rate-limited this account (requests or tokens per minute). Wait a minute."
                ) from error
            if waited >= SLOT_WAIT:
                raise errors.RateLimited(
                    f"{name} allows only a few requests at once for this account, and zero waited "
                    f"{waited:.0f}s for a free slot. Wait for subagents to finish."
                ) from error
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)
            waited += delay


async def load_account(name: str) -> None:
    """Ask the provider which models this key can use, and remember them in `account`."""
    account[name] = set(await api(name).list_models(client(name)))


async def ensure_account(name: str) -> None:
    """load_account() once, ignoring API errors. Without it, model lists show every catalog model."""
    if name not in account:
        try:
            await load_account(name)
        except errors.recoverable():
            pass
