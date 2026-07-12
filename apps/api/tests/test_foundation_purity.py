"""Leaf purity — foundation/ imports only stdlib + pydantic + aos_core.sensitivity
(RFC-0017 / AOS-FOUND-CONTRACTS-001).

Source-scans each foundation module for forbidden import strings rather than
introspecting sys.modules, so a transitively-imported forbidden module (e.g.
pulled in by some unrelated already-imported package) cannot produce a false
positive.
"""
from __future__ import annotations

import ast
from pathlib import Path

import aos_core.foundation as foundation_pkg

_FORBIDDEN_MODULES = ("aos_core.models", "aos_core.services", "aos_core.database", "sqlalchemy", "fastapi", "apps")

_ALLOWED_PREFIXES = ("aos_core.foundation", "aos_core.sensitivity", "aos_core")
# aos_core itself is allowed only via the two leaf submodules below; anything
# else under aos_core.* other than foundation/sensitivity is forbidden too.
_ALLOWED_AOS_CORE_SUBMODULES = ("aos_core.foundation", "aos_core.sensitivity")


def _foundation_source_files() -> list[Path]:
    pkg_dir = Path(foundation_pkg.__file__).parent
    return sorted(p for p in pkg_dir.glob("*.py"))


_PACKAGE_PARTS = ("aos_core", "foundation")


def _resolve_relative(level: int, module: str | None) -> str:
    """Resolve a relative import (as seen from a module inside aos_core.foundation)
    to its fully-qualified dotted name, so ``from ..models import X`` is checked
    just like an absolute import would be."""
    # level=1 -> same package (aos_core.foundation); level=2 -> parent (aos_core).
    base_parts = _PACKAGE_PARTS[: len(_PACKAGE_PARTS) - (level - 1)]
    base = ".".join(base_parts)
    return f"{base}.{module}" if module else base


def _imported_module_names(source: str) -> list[str]:
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module is not None:
                    names.append(node.module)
            else:
                names.append(_resolve_relative(node.level, node.module))
    return names


def test_foundation_modules_only_import_stdlib_pydantic_and_sensitivity() -> None:
    violations: list[str] = []
    for path in _foundation_source_files():
        source = path.read_text(encoding="utf-8")
        for name in _imported_module_names(source):
            top = name.split(".")[0]
            if top == "pydantic":
                continue
            if name.startswith("aos_core"):
                if name == "aos_core" or any(
                    name == allowed or name.startswith(allowed + ".") for allowed in _ALLOWED_AOS_CORE_SUBMODULES
                ):
                    continue
                violations.append(f"{path.name}: forbidden aos_core import {name!r}")
                continue
            # Anything else must be stdlib. We don't have an authoritative stdlib
            # list here, so instead assert it is NOT one of the explicitly
            # forbidden runtime/app modules (belt-and-suspenders on top of the
            # aos_core.* check above).
            for forbidden in _FORBIDDEN_MODULES:
                if name == forbidden or name.startswith(forbidden + "."):
                    violations.append(f"{path.name}: forbidden import {name!r}")
    assert violations == [], "\n".join(violations)


def test_no_forbidden_import_strings_present() -> None:
    """Belt-and-suspenders: a plain substring scan, in case AST parsing above
    ever misses a dynamic/exec-based import pattern."""
    violations: list[str] = []
    for path in _foundation_source_files():
        text = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_MODULES:
            if forbidden == "aos_core.models" and "aos_core.models" in text:
                violations.append(f"{path.name}: mentions aos_core.models")
            if forbidden == "aos_core.services" and "aos_core.services" in text:
                violations.append(f"{path.name}: mentions aos_core.services")
            if forbidden == "aos_core.database" and "aos_core.database" in text:
                violations.append(f"{path.name}: mentions aos_core.database")
            if forbidden in ("sqlalchemy", "fastapi") and f"import {forbidden}" in text:
                violations.append(f"{path.name}: mentions import {forbidden}")
    assert violations == [], "\n".join(violations)
