"""Tests for atlas.db — schema initialisation and basic operations."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from atlas.constants import EMBEDDING_DIM
from atlas.db import get_db_connection, init_db


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


class TestInitDb:
    def test_creates_articles_table(self, db_path: Path) -> None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_articles_fts_table(self, db_path: Path) -> None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE name='articles_fts'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent(self, tmp_path: Path) -> None:
        path = tmp_path / "idempotent.db"
        init_db(path)
        init_db(path)  # must not raise


class TestArticlesTable:
    def test_insert_and_retrieve(self, db_path: Path) -> None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO articles (path, title, importance, maturity, created, last_compiled) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            ("wiki/domains/foo.md", "Foo", 75, "validated"),
        )
        conn.commit()
        cursor.execute("SELECT title, importance FROM articles WHERE path = ?", ("wiki/domains/foo.md",))
        row = cursor.fetchone()
        assert row["title"] == "Foo"
        assert row["importance"] == 75
        conn.close()

    def test_fts_search(self, db_path: Path) -> None:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO articles (path, title, importance, maturity, created, last_compiled) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            ("wiki/domains/rag.md", "RAG Overview", 60, "draft"),
        )
        article_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO articles_fts (rowid, title, content, path) VALUES (?, ?, ?, ?)",
            (article_id, "RAG Overview", "Retrieval Augmented Generation combines retrieval.", "wiki/domains/rag.md"),
        )
        conn.commit()
        cursor.execute(
            "SELECT title FROM articles_fts WHERE articles_fts MATCH 'retrieval' ORDER BY rank LIMIT 5"
        )
        rows = cursor.fetchall()
        assert len(rows) >= 1
        assert rows[0]["title"] == "RAG Overview"
        conn.close()
