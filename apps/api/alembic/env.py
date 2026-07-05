"""Alembic environment for the ArchetypeOS API.

The database URL is read from application settings
(``app.config.get_settings().database_url``) rather than from ``alembic.ini``,
so migrations always target the same database the app uses: sqlite in dev/test
and Postgres in the container.

``app.models`` is imported for its side effect of registering all ORM tables on
``Base.metadata``; that metadata is the autogenerate target.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the app package (apps/api/app) is importable when alembic runs from
# apps/api/. The directory containing this file is apps/api/alembic, so its
# parent is apps/api, which holds the `app` package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aos_core.config import get_settings  # noqa: E402
from aos_core.database import Base  # noqa: E402
import aos_core.models  # noqa: E402,F401  (registers all tables on Base.metadata)

# Alembic Config object, providing access to values in alembic.ini.
config = context.config

# Supply the database URL from application settings (overrides the blank ini value).
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Configure Python logging from the ini file, if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate — all 20 ORM tables register here.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to a script, no DBAPI)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live DBAPI connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
