from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from .config import get_settings


def _connect_args(url: str) -> dict:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


def _is_file_sqlite(url: str) -> bool:
    """True only for a file-backed sqlite URL (never ``:memory:`` or Postgres).

    ``sqlite://`` / ``sqlite:///`` with no path is an in-memory database and
    must be left untouched, as must any non-sqlite URL.
    """
    if not url.startswith("sqlite"):
        return False
    if ":memory:" in url:
        return False
    return url not in ("sqlite://", "sqlite:///")


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


if _is_file_sqlite(settings.database_url):
    # A file-based sqlite DB can be written by the API and the worker at once
    # (the e2e stack runs both against one file). WAL lets readers and a single
    # writer proceed concurrently, and a 30s busy_timeout makes a briefly-locked
    # writer wait rather than immediately raising "database is locked". Applied
    # per raw DBAPI connection; :memory: and Postgres engines never reach here,
    # and the test suites build their own engines, so their behavior is unchanged.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        finally:
            cursor.close()


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
