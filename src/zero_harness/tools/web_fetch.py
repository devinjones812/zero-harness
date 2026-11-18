from parallel import Parallel

from zero_harness import config
from zero_harness.tools import openai_web

SCHEMA = {
    "type": "function",
    "name": "web_fetch",
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
        return openai_web.run(url=url, objective=objective)
    focus = {"objective": objective} if objective else {}
    return Parallel().extract(urls=[url], max_chars_total=20000, **focus).model_dump_json()
