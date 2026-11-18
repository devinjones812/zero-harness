from parallel import Parallel

SCHEMA = {
    "type": "function",
    "name": "web_search",
    "description": "Search the web. Returns JSON results with url, title, and text excerpts.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}


def run(query: str) -> str:
    result = Parallel().search(objective=query, search_queries=[query], max_chars_total=10000)
    return result.model_dump_json()
