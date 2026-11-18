from parallel import Parallel


def search(query: str) -> str:
    """Return Parallel search results with excerpts."""
    result = Parallel().search(objective=query, search_queries=[query], max_chars_total=10000)
    return result.model_dump_json()


def fetch(url: str, objective: str | None) -> str:
    """Return page text from Parallel's Extract API."""
    focus = {"objective": objective} if objective else {}
    return Parallel().extract(urls=[url], max_chars_total=20000, **focus).model_dump_json()
