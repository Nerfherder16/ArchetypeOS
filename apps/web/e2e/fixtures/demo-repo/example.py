"""Tiny sample module so the read-only scanner detects Python.

This fixture repository intentionally has no tests and no CI config so the
scanner emits MISSING_TESTS and NO_CI_CONFIG risk flags, and its Dockerfile
(without an .env template) emits DOCKER_WITHOUT_ENV_TEMPLATE. The e2e suite
asserts on those deterministic signals.
"""


def add(a: int, b: int) -> int:
    return a + b


def greet(name: str) -> str:
    return f"hello, {name}"
