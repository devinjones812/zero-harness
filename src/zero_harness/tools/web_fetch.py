from zero_harness.web import backend

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
    return backend.choose().fetch(url, objective)
