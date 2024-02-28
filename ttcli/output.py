from typing import Any

from rich.console import Console


class _Printer:
    console = Console(highlight=False)

    def __call__(self, text: str | Any, nl=True):
        self.console.print(text, end="\n" if nl else "")


print = _Printer()
