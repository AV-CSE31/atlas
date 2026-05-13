"""Database initialisation for the Atlas Knowledge Compiler.

Provides a single entry-point for creating a SQLite connection with
``sqlite-vec`` loaded, and a function to bootstrap the schema (FTS5 + vector
tables) when the database is first created.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import sqlite_vec

from .constants import EMBEDDING_DIM

logger = logging.getLogger(__name__)


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Open and return a SQLite connection with sqlite-vec loaded.

    The connection's ``row_factory`` is set to :class:`sqlite3.Row` so that
    result rows support both index and name-based access.  Extension loading
    is disabled after ``sqlite_vec`` is loaded.

    Args:
        db_path: Absolute or relative path to the ``atlas.db`` SQLite file.

    Returns:
        An open :class:`sqlite3.Connection` instance.
    """
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    """Initialise the SQLite database schema if it does not already exist.

    Creates three tables:

    * ``articles`` — core metadata (path, title, importance, maturity, dates).
    * ``articles_fts`` — FTS5 virtual table for full-text BM25 search.
    * ``articles_vec`` — sqlite-vec virtual table for KNN vector search.

    Existing tables are left untouched (``CREATE … IF NOT EXISTS``).

    Args:
        db_path: Absolute or relative path to the ``atlas.db`` SQLite file.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            title TEXT,
            importance INTEGER DEFAULT 50,
            maturity TEXT DEFAULT 'draft',
            created TEXT,
            last_compiled TEXT
        )
    """)

    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            content,
            path UNINDEXED
        )
    """)

    # Drop any stale auto-sync triggers from earlier schema versions
    cursor.executescript("""
        DROP TRIGGER IF EXISTS articles_ai;
        DROP TRIGGER IF EXISTS articles_ad;
        DROP TRIGGER IF EXISTS articles_au;
    """)

    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_vec USING vec0(
            id INTEGER PRIMARY KEY,
            embedding float[{EMBEDDING_DIM}]
        )
    """)

    conn.commit()
    conn.close()
    logger.debug("Database schema initialised at %s", db_path)
