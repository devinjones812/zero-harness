from parallel import Parallel

from zero_harness import config
from zero_harness.tools import openai_web

SCHEMA = {
    "type": "function",
    "name": "web_search",
    "description": "Search the web. Returns findings and source URLs as JSON.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}


def run(query: str) -> str:
    if config.provider("search_provider") == "openai":
        return openai_web.run(query=query)
    result = Parallel().search(objective=query, search_queries=[query], max_chars_total=10000)
    return result.model_dump_json()
