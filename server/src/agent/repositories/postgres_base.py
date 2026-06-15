"""Shared PostgreSQL repository helpers."""

from __future__ import annotations

from contextlib import contextmanager

from agent.config import get_settings
from agent.repositories.postgres_schema_manager import PostgresSchemaManager


class PostgresRepositoryBase:
    """Base repository with lazy psycopg connection and schema preparation."""

    def __init__(self, schema_manager: PostgresSchemaManager | None = None) -> None:
        self._schema_manager = schema_manager or PostgresSchemaManager()

    def _connect(self):
        """Open a PostgreSQL connection when psycopg and DSN are available."""

        return self._open_connection(autocommit=True)

    def _connect_for_transaction(self):
        """Open a PostgreSQL connection dedicated to explicit write transactions."""

        return self._open_connection(autocommit=False)

    @contextmanager
    def _transaction(self):
        """Yield a transactional PostgreSQL connection with rollback on failure."""

        conn = self._connect_for_transaction()
        if conn is None:
            yield None
            return
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _open_connection(self, *, autocommit: bool):
        """Open a PostgreSQL connection and ensure schema readiness."""

        settings = get_settings()
        if not settings.postgres_dsn:
            return None
        try:
            import psycopg
        except ImportError:
            return None
        try:
            conn = psycopg.connect(settings.postgres_dsn, autocommit=autocommit)
        except Exception:
            return None
        self._schema_manager.ensure_schema(conn)
        if not autocommit:
            conn.commit()
        return conn
