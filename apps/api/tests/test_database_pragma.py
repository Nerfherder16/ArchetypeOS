"""Guard for the sqlite WAL/busy_timeout enablement (AOS-COUNCIL-PHASEC2B).

`aos_core.database` enables `PRAGMA journal_mode=WAL` + `busy_timeout` so the
API and the worker can share one file-based sqlite DB in the e2e stack. The
enablement is gated on `_is_file_sqlite`, which MUST leave `:memory:`, the empty
`sqlite://` URL, and Postgres untouched — WAL on `:memory:` is meaningless and
touching Postgres would be wrong. This pins that predicate (LES-020: a core
change needs a test in the same change set, even a small infra tweak).
"""

from __future__ import annotations

from aos_core.database import _is_file_sqlite


def test_is_file_sqlite_true_for_file_backed_urls() -> None:
    assert _is_file_sqlite("sqlite:////tmp/aos.db") is True
    assert _is_file_sqlite("sqlite:///relative.db") is True


def test_is_file_sqlite_false_for_memory_and_empty() -> None:
    assert _is_file_sqlite("sqlite:///:memory:") is False
    assert _is_file_sqlite("sqlite://:memory:") is False
    assert _is_file_sqlite("sqlite://") is False
    assert _is_file_sqlite("sqlite:///") is False


def test_is_file_sqlite_false_for_non_sqlite() -> None:
    assert _is_file_sqlite("postgresql+psycopg://user@host/db") is False
    assert _is_file_sqlite("postgresql://user@host/db") is False
