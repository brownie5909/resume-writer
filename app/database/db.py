import os
import re
import sqlite3
from contextlib import contextmanager

# Optional PostgreSQL support. SQLite remains the fallback when DATABASE_URL is not set.
try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import IntegrityError as PostgresIntegrityError
except ImportError:  # pragma: no cover - only used when psycopg2 is not installed locally
    psycopg2 = None
    PostgresIntegrityError = Exception

# Database setup
DB_PATH = "hire_ready.db"
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)


class DatabaseCursor:
    """Small wrapper so existing SQLite-style queries also work with PostgreSQL."""

    def __init__(self, cursor, use_postgres: bool):
        self.cursor = cursor
        self.use_postgres = use_postgres

    def _convert_query(self, query: str) -> str:
        if not self.use_postgres:
            return query

        converted = query.replace("?", "%s")
        converted = re.sub(r"datetime\('now', '-(\d+) days'\)", r"CURRENT_TIMESTAMP - INTERVAL '\1 days'", converted)
        return converted

    def execute(self, query: str, params=None):
        params = params or ()
        return self.cursor.execute(self._convert_query(query), params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount


class DatabaseConnection:
    """Small wrapper that provides a consistent cursor() method."""

    def __init__(self, conn, use_postgres: bool):
        self.conn = conn
        self.use_postgres = use_postgres

    def cursor(self):
        if self.use_postgres:
            return DatabaseCursor(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor), True)
        return DatabaseCursor(self.conn.cursor(), False)

    def commit(self):
        return self.conn.commit()

    def close(self):
        return self.conn.close()


class RowDict(dict):
    """Dictionary row that also supports numeric index access used in older code."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _sqlite_row_factory(cursor, row):
    return RowDict({col[0]: row[idx] for idx, col in enumerate(cursor.description)})


def _normalize_postgres_row(row):
    if row is None:
        return None
    return RowDict(row)


def _connect_raw():
    if USE_POSTGRES:
        if psycopg2 is None:
            raise RuntimeError("DATABASE_URL is set but psycopg2 is not installed.")
        return psycopg2.connect(DATABASE_URL, sslmode="require")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _sqlite_row_factory
    return conn


def _execute_schema(cursor, sqlite_sql: str, postgres_sql: str = None):
    cursor.execute(postgres_sql if USE_POSTGRES and postgres_sql else sqlite_sql)


def init_database():
    """Initialize database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                tier TEXT DEFAULT 'free',
                is_verified BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                is_admin BOOLEAN DEFAULT FALSE
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS resume_documents (
                document_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                resume_text TEXT,
                cover_letter_text TEXT,
                template TEXT DEFAULT 'default',
                pdf_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS resume_versions (
                version_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT,
                resume_text TEXT,
                cover_letter_text TEXT,
                template TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES resume_documents (document_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS resume_analysis_results (
                analysis_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                original_filename TEXT,
                original_content_type TEXT,
                original_file_base64 TEXT,
                original_resume_text TEXT,
                target_role TEXT,
                analysis_json TEXT,
                overall_score INTEGER,
                ats_score INTEGER,
                improved_resume TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES resume_documents (document_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS cover_letter_optimiser_results (
                optimisation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                original_text TEXT NOT NULL,
                target_role TEXT,
                company_name TEXT,
                job_posting TEXT,
                analysis_json TEXT,
                overall_score INTEGER,
                ats_score INTEGER,
                improved_cover_letter TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS usage_tracking (
                usage_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                month_year TEXT NOT NULL,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, feature_name, month_year)
            )
            """
        )

        _execute_schema(
            cursor,
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                reset_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        conn.commit()


@contextmanager
def get_db():
    """Database connection context manager."""
    raw_conn = _connect_raw()
    conn = DatabaseConnection(raw_conn, USE_POSTGRES)
    try:
        yield conn
    finally:
        conn.close()
