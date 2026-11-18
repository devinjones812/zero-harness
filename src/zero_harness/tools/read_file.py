from pathlib import Path

from zero_harness import images

DEFAULT_LIMIT = 2000

SCHEMA = {
    "type": "function",
    "name": "read_file",
    "description": (
        "Read a text file or view an image (png, jpg, gif, webp). Each text line starts with its line number and '|'. "
        "The number and '|' are not part of the file; don't include them in edit_file old_text. "
        f"Use offset and limit to read part of a large file. Default limit: {DEFAULT_LIMIT} lines."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer", "description": "First line to read, starting at 1. Default: 1."},
            "limit": {"type": "integer", "description": "Max number of lines to read."},
        },
        "required": ["path"],
    },
}


def run(path: str, offset: int = 1, limit: int = DEFAULT_LIMIT) -> str | list:
    if images.is_image(path):
        return [images.content(path)]
    lines = Path(path).read_text().splitlines()
    start = max(offset, 1)
    end = start + limit - 1
    output = "\n".join(f"{number:6}|{line}" for number, line in enumerate(lines[start - 1 : end], start))
    if end < len(lines):
        output += f"\n(showing lines {start}-{end} of {len(lines)}. Use offset to read more.)"
    return output or "(empty file)"
