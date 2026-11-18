from zero_harness import config
from zero_harness.providers import openai_web, parallel_web

SCHEMA = {
    "type": "function",
    "name": "parallel_search" if config.get("search_provider") == "parallel" else "openai_search",
    "description": "Search the web. Returns findings and source URLs as JSON.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}


def run(query: str) -> str:
    if config.provider("search_provider") == "openai":
        return openai_web.search(query)
    return parallel_web.search(query)
