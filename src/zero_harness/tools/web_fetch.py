from parallel import Parallel

SCHEMA = {
    "type": "function",
    "name": "web_fetch",
    "description": "Read a web page. Returns its text as JSON. Give an objective to get only the relevant parts.",
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
    focus = {"objective": objective} if objective else {}
    return Parallel().extract(urls=[url], max_chars_total=20000, **focus).model_dump_json()
