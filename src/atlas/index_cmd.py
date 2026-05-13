"""Index command for the Atlas Knowledge Compiler.

Reads all compiled wiki articles from ``wiki/domains/``, extracts their
front-matter metadata, and (re-)populates the FTS5 and vector tables in
``atlas.db``.
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path

import typer
import yaml

from .constants import WIKI_DOMAINS_PATH
from .db import get_db_connection
from .embeddings import get_embedding

logger = logging.getLogger(__name__)


def index_cmd(base_path: Path = Path(".")) -> None:
    """Rebuild the full-text and vector search indexes from wiki articles.

    Deletes all existing rows from ``articles``, ``articles_fts``, and
    ``articles_vec`` before re-indexing, making each run idempotent.

    Args:
        base_path: Root directory of the Atlas knowledge base.
    """
    typer.echo("Indexing wiki articles...")
    db_path = base_path / "atlas.db"
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM articles")
    cursor.execute("DELETE FROM articles_vec")
    cursor.execute("DELETE FROM articles_fts")

    domains_dir = base_path / WIKI_DOMAINS_PATH
    if not domains_dir.exists():
        typer.echo("No wiki/domains directory found — nothing to index.")
        conn.close()
        return

    count = 0
    for file_path in domains_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            logger.warning("Could not read %s: %s — skipping.", file_path, exc)
            continue

        title = file_path.stem
        importance = 50
        maturity = "draft"

        if content.startswith("---"):
            end_fm = content.find("---", 3)
            if end_fm != -1:
                try:
                    fm = yaml.safe_load(content[3:end_fm])
                    title = fm.get("title", title)
                    importance = fm.get("importance", 50)
                    maturity = fm.get("maturity", "draft")
                except yaml.YAMLError as exc:
                    logger.warning(
                        "YAML front-matter parse error in %s: %s", file_path.name, exc
                    )

        rel_path = str(file_path.relative_to(base_path)).replace("\\", "/")
        cursor.execute(
            "INSERT INTO articles (path, title, importance, maturity, created, last_compiled) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            (rel_path, title, importance, maturity),
        )
        article_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO articles_fts (rowid, title, content, path) VALUES (?, ?, ?, ?)",
            (article_id, title, content, rel_path),
        )

        emb = get_embedding(content)
        emb_bytes = struct.pack(f"{len(emb)}f", *emb)
        try:
            cursor.execute(
                "INSERT INTO articles_vec (id, embedding) VALUES (?, ?)",
                (article_id, emb_bytes),
            )
        except Exception as exc:
            logger.warning(
                "Vector insert failed for article id=%s (%s): %s",
                article_id,
                file_path.name,
                exc,
            )

        count += 1

    conn.commit()
    conn.close()
    typer.echo(f"Successfully indexed {count} articles.")
