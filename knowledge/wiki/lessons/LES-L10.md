# LES-L10 — a service-level DB test fixture must import the models module, or create_all silently omits new tables (test-order-dependent failure)

## Aliases

- no such table in a service test but the API test passes
- db_session fixture missing table
- Base.metadata.create_all skips a model
- test passes or fails depending on run order
- new SQLAlchemy model not created in hermetic fixture

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- While building AOS-CONNECTOR-001, a new `db_session` conftest fixture created tables with `Base.metadata.create_all(bind=engine)` after `from aos_core.database import Base` — but did **not** import `aos_core.models`.
- `Base.metadata` only knows about tables whose model classes have been imported (import is what registers a mapped class on the shared `MetaData`). So `create_all` emitted DDL only for models already imported by something else in the process.
- Symptom: `sqlite3.OperationalError: no such table: connectors` — but only for the **first** service-level test in the run. Later service tests passed, because by then the `client` fixture had imported `app.main` (which imports the routes, which import the models), registering every table globally on `Base.metadata`. The result was a test that passed or failed purely by ordering.

## Linked Decisions / Projects

- `apps/api/tests/conftest.py` — the shared `db_session` fixture (added in AOS-CONNECTOR-001)
- AOS-CONNECTOR-001 — `packages/aos_core/aos_core/services/connectors.py`, `apps/api/tests/test_connectors_api.py`
- [[LES-L09]] — a sibling "the check aggregated across the wrong scope" ordering/scope gotcha

## Content

- Event: a hermetic fixture that was only accidentally hermetic — it relied on another fixture in the same session having imported the models first.
- Root cause: `create_all` reflects the state of `Base.metadata` at call time, and a model is absent from that metadata until its module is imported. A bare `import aos_core.database` does not pull in the model classes.
- Fix: import the models module inside the fixture before `create_all`:

  ```python
  import aos_core.models  # noqa: F401 — register every table on Base.metadata
  from aos_core.database import Base
  ...
  Base.metadata.create_all(bind=engine)
  ```

- General rule: any fixture (or script) that builds a schema from `Base.metadata` must ensure every model module is imported first. Prefer a single `import <pkg>.models` (or an `__init__` that imports all models) over trusting import side effects from unrelated code paths. If a test's outcome changes with `-p no:randomly` / reordering, suspect metadata-registration order, not the logic under test.
