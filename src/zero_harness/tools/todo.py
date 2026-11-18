from zero_harness.ui.notes import note

SCHEMA = {
    "type": "function",
    "name": "todo",
    "description": (
        "Write the plan for a task with 3 or more steps as a checklist, then update it as you work. "
        "Send the full list every time. Keep exactly one item in_progress while working."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "done"]},
                    },
                    "required": ["text", "status"],
                },
            },
        },
        "required": ["items"],
    },
}

MARKS = {"pending": ("☐", "default"), "in_progress": ("▶", "bold cyan"), "done": ("✓", "dim")}


def run(items: list[dict]) -> str:
    for item in items:
        mark, style = MARKS[item["status"]]
        note(f"{mark} {item['text']}", style=style)
    return "ok"
