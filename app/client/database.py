"""SQLAlchemy database setup — SQLite-backed session factory."""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DB_DIR = Path(__file__).resolve().parents[2] / "data" / "database"
_DB_PATH = _DB_DIR / "agent.db"


class DatabaseManager:
    """Manages the SQLAlchemy engine and session factory.

    Follows the same lifecycle pattern as :class:`rag.client.milvus.MilvusManager`:
    ``init()`` in lifespan startup, ``close()`` in lifespan shutdown.
    """

    def __init__(self):
        self.engine = None
        self._session_factory = None

    def init(self) -> None:
        """Create engine, session factory, and ensure tables exist."""
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{_DB_PATH}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self._session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        import app.server.models  # noqa: F401 — register models on Base.metadata

        Base.metadata.create_all(bind=self.engine)

        # ── Migrations for existing databases ────────────────────────
        self._run_migrations()

    @staticmethod
    def _column_exists(engine, table: str, column: str) -> bool:
        """Check if a column exists in a SQLite table via PRAGMA."""
        from sqlalchemy import text

        with engine.connect() as conn:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            return any(row[1] == column for row in rows)

    def _run_migrations(self) -> None:
        """Apply schema changes that ``create_all`` won't handle."""
        with self.engine.connect() as conn:
            if not self._column_exists(self.engine, "documents", "status"):
                conn.execute(
                    text(
                        "ALTER TABLE documents ADD COLUMN status VARCHAR "
                        "NOT NULL DEFAULT 'uploaded'"
                    )
                )
                conn.commit()

            # ── v2: metadata column ──────────────────────────────
            # ``metadata`` clashes with ``Base.metadata`` in SQLAlchemy so
            # ``create_all`` skips it — add it manually.
            if not self._column_exists(self.engine, "documents", "metadata"):
                conn.execute(
                    text(
                        "ALTER TABLE documents ADD COLUMN metadata TEXT "
                        "DEFAULT '{}' NOT NULL"
                    )
                )
                conn.commit()

    def get_session(self) -> Session:
        """Create a new scoped session (caller must close)."""
        if self._session_factory is None:
            raise RuntimeError("DatabaseManager not initialized — call init() first")
        return self._session_factory()

    def close(self) -> None:
        """Dispose the engine, releasing any connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self._session_factory = None


# Module-level singleton — imported in lifespan & dependencies.
db_manager = DatabaseManager()


class Base(DeclarativeBase):
    pass
