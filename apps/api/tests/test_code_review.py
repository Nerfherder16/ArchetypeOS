"""Tests for the Tier-1 local code reviewer (AOS-LLM-REVIEW-001).

Hermetic: a fake provider stands in for the LLM, so no test touches a model or
the network. Verifies aggregation across per-category passes, the code-only
filter, and the fail-open contract (a reviewer must never raise / block).
"""
from __future__ import annotations

import types

from aos_core.services.code_review import (
    CATEGORY_CHECKS,
    ReviewFinding,
    filter_code_files,
    review_diff,
)

_CODE_DIFF = (
    "diff --git a/x.py b/x.py\n"
    "--- a/x.py\n+++ b/x.py\n"
    "@@ -0,0 +1,2 @@\n+def div(a, b):\n+    return a / b\n"
)
_DOCS_DIFF = (
    "diff --git a/README.md b/README.md\n"
    "--- a/README.md\n+++ b/README.md\n@@ -0,0 +1 @@\n+# hello\n"
)


class _FakeProvider:
    """Returns a per-category payload; can be told to raise on some categories."""

    def __init__(self, by_category: dict | None = None, raise_on: set | None = None):
        self.by_category = by_category or {}
        self.raise_on = raise_on or set()
        self.calls = 0

    def generate(self, *, system, prompt, max_tokens=512, response_format=None):
        self.calls += 1
        cat = next((c for c in CATEGORY_CHECKS if f"class: {c}" in system), "?")
        if cat in self.raise_on:
            raise RuntimeError("provider boom")
        return types.SimpleNamespace(text=self.by_category.get(cat, '{"findings": []}'))


def test_filter_code_files_keeps_code_drops_docs():
    out = filter_code_files(_CODE_DIFF + _DOCS_DIFF)
    assert "x.py" in out
    assert "README.md" not in out


def test_review_diff_runs_one_pass_per_category_and_aggregates():
    prov = _FakeProvider(
        by_category={
            "edge_cases": '{"findings":[{"severity":"bug","location":"x.py:div",'
            '"issue":"no guard for b==0"}]}'
        }
    )
    findings = review_diff(prov, _CODE_DIFF)
    assert prov.calls == len(CATEGORY_CHECKS)  # one focused pass per category
    assert len(findings) == 1
    assert isinstance(findings[0], ReviewFinding)
    assert findings[0].category == "edge_cases"
    assert findings[0].severity == "bug"
    assert "b==0" in findings[0].issue


def test_review_diff_fail_open_when_provider_raises():
    prov = _FakeProvider(raise_on=set(CATEGORY_CHECKS))
    # Must not raise; a fully-failing provider yields no findings.
    assert review_diff(prov, _CODE_DIFF) == []


def test_review_diff_ignores_unparseable_output():
    prov = _FakeProvider(by_category={"correctness": "sorry, I cannot comply"})
    assert review_diff(prov, _CODE_DIFF) == []


def test_review_diff_empty_on_docs_only_diff():
    prov = _FakeProvider(
        by_category={"correctness": '{"findings":[{"severity":"bug","location":"a","issue":"x"}]}'}
    )
    # Docs-only diff is filtered to nothing → the provider is never called.
    assert review_diff(prov, _DOCS_DIFF) == []
    assert prov.calls == 0


def test_review_finding_as_line():
    f = ReviewFinding(category="resource", severity="bug", location="x.py:f", issue="leak")
    assert f.as_line() == "[bug] resource x.py:f — leak"
