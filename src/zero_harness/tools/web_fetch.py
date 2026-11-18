from zero_harness import config
from zero_harness.providers import openai_web, parallel_web

SCHEMA = {
    "type": "function",
    "name": "parallel_fetch" if config.get("search_provider") == "parallel" else "openai_fetch",
    "description": "Read a public web page. Returns a cited summary or excerpts as JSON. Give an objective to focus it.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "objective": {"type": "string", "description": "Optional. What you are looking for on the page."},
        },
        "required": ["url"],
    },
}


def run(url: str, objective: str | None = None) -> str:
    if config.provider("search_provider") == "openai":
        return openai_web.fetch(url, objective)
    return parallel_web.fetch(url, objective)
