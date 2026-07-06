"""Entry point for the sample app: wires the core service to a CLI.

The README is deliberately thin — the substance lives here in the code.
"""

from __future__ import annotations

from core import Engine


def run(argv: list[str] | None = None) -> str:
    """Build an Engine and return its rendered greeting."""
    engine = Engine(name="sample")
    return engine.greet()


class App:
    """Thin application shell that owns an Engine."""

    def __init__(self) -> None:
        self.engine = Engine(name="app")

    def main(self) -> str:
        return self.engine.greet()
