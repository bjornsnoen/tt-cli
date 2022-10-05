from typing import Any

from rich.console import Console


def print(text: str | Any, nl=True):
    if not hasattr(print, "console"):
        print.console = Console(highlight=False)

    print.console.print(text, end="\n" if nl else "")
