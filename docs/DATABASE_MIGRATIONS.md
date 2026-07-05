# Database Migrations (Alembic)

ArchetypeOS uses [Alembic](https://alembic.sqlalchemy.org/) to version the API
database schema. This document is the migration discipline and runbook.

## Scope

- Applies to the API database defined by `apps/api/app/models.py` (all ORM
  tables register on `Base.metadata`).
- The worker does not run migrations (separate DB access pattern; not needed for
  the baseline).
- Runtime DB is Postgres (`docker-compose.yml` api service). Dev/test default is
  sqlite. Migrations are **model-driven** — the DDL is rendered from the ORM
  metadata (via the `GUID` / `JSONField` `TypeDecorator`s), so it is portable
  across sqlite and Postgres.

## How the pieces fit

- `apps/api/alembic.ini` — Alembic config. `script_location = alembic`.
  `sqlalchemy.url` is intentionally **blank**.
- `apps/api/alembic/env.py` — imports `Base` from `app.database` and
  `import app.models` (so all tables register on `Base.metadata`), sets
  `target_metadata = Base.metadata`, and reads the database URL from
  `app.config.get_settings().database_url` (NOT from `alembic.ini`). Autogenerate
  runs with `compare_type=True`.
- `apps/api/alembic/versions/0001_baseline.py` — the baseline migration. It
  creates the full current schema (20 tables) with `down_revision = None`.
- `apps/api/docker-entrypoint.sh` — runs `alembic upgrade head` **before**
  `uvicorn`. A failed migration exits non-zero, so the container never serves a
  broken schema.

`app.database.init_db()` (`Base.metadata.create_all`) is still called on API
startup. On fresh Postgres, alembic runs first (in the entrypoint, before
uvicorn), so `create_all` is a no-op. It only builds schema for sqlite dev,
where no container entrypoint runs. A later package retires it once a real
migration exercises the path end to end.

## Running migrations locally

Run all alembic commands from `apps/api/` with `PYTHONPATH=.` so `import app...`
resolves (the app package is at `apps/api/app`). The URL comes from
`DATABASE_URL` (env.py reads settings), not from `alembic.ini`.

```sh
cd apps/api

# Apply all migrations (creates the schema on a fresh DB):
DATABASE_URL=sqlite:////tmp/aos.db PYTHONPATH=. alembic upgrade head

# Show the current revision:
DATABASE_URL=sqlite:////tmp/aos.db PYTHONPATH=. alembic current

# Roll back one step (or to a base):
DATABASE_URL=sqlite:////tmp/aos.db PYTHONPATH=. alembic downgrade -1
DATABASE_URL=sqlite:////tmp/aos.db PYTHONPATH=. alembic downgrade base
```

For Postgres, set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`.

## Authoring a new migration

1. Change the ORM models in `apps/api/app/models.py`.
2. Autogenerate a candidate migration against a database already at `head`:

   ```sh
   cd apps/api
   DATABASE_URL=<url-at-head> PYTHONPATH=. alembic revision --autogenerate -m "describe the change"
   ```

3. **Inspect the generated DDL before committing.** This is a hard rule.
   Autogenerate is a draft, not an authority:
   - Confirm the `upgrade()` / `downgrade()` operations match the intent and
     nothing unexpected was added or dropped.
   - Confirm custom types render as `app.models.GUID()` / `app.models.JSONField()`
     and that `import app.models` is present at the top of the file (autogenerate
     does not always emit this import — add it if missing, or the migration will
     raise `NameError` at run time).
   - Autogenerate does **not** detect every change (e.g. server-default value
     edits, some constraint renames, CHECK constraints). Hand-edit as needed.
   - Keep migrations model-driven (render from metadata) so the DDL stays
     portable across sqlite and Postgres.
4. Apply and round-trip test: `alembic upgrade head` then
   `alembic downgrade -1` (or `base`), on both sqlite and — via CI compose-smoke
   — Postgres.

## No-drift gate (the correctness check)

After `alembic upgrade head`, a fresh autogenerate against that database MUST
produce an **empty** migration (`upgrade()`/`downgrade()` are just `pass`). A
non-empty result means the migrations no longer match the models — fix the
migration (or the models) until it is empty.

```sh
cd apps/api
DATABASE_URL=<url-at-head> PYTHONPATH=. alembic revision --autogenerate -m drift-probe
# inspect the generated file: upgrade() and downgrade() must be empty
rm apps/api/alembic/versions/*drift-probe*   # never commit the probe
```

## Runbook: stamping a pre-existing populated database

The baseline migration reproduces the **current** schema. A database that was
built by the old `create_all` path (e.g. the populated database on teevee-1)
already has all 20 tables — running the baseline against it would try to
re-create them and fail. Such a database must be **stamped**, not upgraded, so
Alembic records that it is already at the baseline revision without running the
DDL:

```sh
cd apps/api
DATABASE_URL=<prod-url> PYTHONPATH=. alembic stamp head
```

This is a **one-time** operation per pre-existing database. After stamping,
`alembic current` reports the baseline revision and subsequent migrations apply
normally. Fresh databases (no tables) get the schema from `alembic upgrade head`
instead and must NOT be stamped.

## Verification summary

- Fresh `alembic upgrade head` on an empty DB creates 20 model tables +
  `alembic_version` (21 total).
- No-drift: post-upgrade `alembic revision --autogenerate` yields an empty
  migration.
- Round-trip: `alembic downgrade base` drops all baseline tables cleanly.
- CI `compose-smoke` runs the entrypoint (baseline) against real Postgres and
  polls `/health` — the authoritative proof of the Postgres migration path.
