"""Core domain logic: the reusable Engine the app is built around."""

from __future__ import annotations

__all__ = ["Engine", "build_default"]


class Engine:
    """Renders greetings; the reusable heart of the sample app."""

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"hello from {self.name}"


def build_default() -> Engine:
    """Construct an Engine with a default name."""
    return Engine(name="default")
