from zero_harness.web import backend

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
    return backend.choose().search(query)
