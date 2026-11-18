from zero_harness import config
from zero_harness.ui.notes import note

DESCRIPTION = "Toggle auto mode: Jev approves routine bash commands; risky ones still ask. /auto on|off also works."


def run(history: list, args: str) -> None:
    enabled = {"on": True, "off": False}.get(args, not config.get("auto"))
    config.update("auto", enabled)
    note(f"auto mode: {'on' if enabled else 'off'} (saved)")
