"""Search command for the Atlas Knowledge Compiler.

Implements hybrid search (BM25 FTS5 + vector KNN) over compiled wiki articles
stored in ``atlas.db``.
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path

import typer

from .constants import MAX_QUERY_LENGTH, SEARCH_RESULT_LIMIT
from .db import get_db_connection
from .embeddings import get_embedding

logger = logging.getLogger(__name__)


def search_cmd(query: str, base_path: Path = Path(".")) -> None:
    """Run a hybrid keyword + semantic search against the compiled wiki.

    Validates and sanitises the query, runs an FTS5 keyword search and a
    vector KNN search independently, and prints ranked results for each.

    Args:
        query: The natural-language query string (max
            :data:`~atlas.constants.MAX_QUERY_LENGTH` characters).
        base_path: Root directory of the Atlas knowledge base.

    Raises:
        typer.Exit: If the query is empty or exceeds the maximum length.
    """
    query = query.strip()
    if not query:
        typer.echo("Error: query must not be empty.", err=True)
        raise typer.Exit(1)
    if len(query) > MAX_QUERY_LENGTH:
        typer.echo(
            f"Error: query exceeds maximum length of {MAX_QUERY_LENGTH} characters.", err=True
        )
        raise typer.Exit(1)

    typer.echo(f"Searching for: '{query}'...")
    db_path = base_path / "atlas.db"
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # --- FTS5 keyword search ---
    typer.echo("\n--- FTS Keyword Matches ---")
    try:
        cursor.execute(
            "SELECT rowid, title, path, "
            "snippet(articles_fts, 1, '[', ']', '...', 10) as snip "
            "FROM articles_fts WHERE articles_fts MATCH ? ORDER BY rank "
            f"LIMIT {SEARCH_RESULT_LIMIT}",
            (query,),
        )
        rows = cursor.fetchall()
    except Exception as exc:
        logger.error("FTS search failed: %s", exc)
        rows = []

    if not rows:
        typer.echo("No keyword matches found.")
    else:
        for r in rows:
            typer.echo(f"\n{r['title']} ({r['path']})\n   {r['snip']}")

    # --- Vector semantic search ---
    typer.echo("\n--- Semantic Vector Matches ---")
    emb = get_embedding(query)
    emb_bytes = struct.pack(f"{len(emb)}f", *emb)
    try:
        cursor.execute(
            "SELECT a.title, a.path, v.distance "
            "FROM articles_vec v JOIN articles a ON v.id = a.id "
            f"WHERE v.embedding MATCH ? AND k = {SEARCH_RESULT_LIMIT}",
            (emb_bytes,),
        )
        vec_rows = cursor.fetchall()
        if not vec_rows:
            typer.echo("No semantic matches found.")
        else:
            for r in vec_rows:
                typer.echo(f"\n{r['title']} ({r['path']}) - dist: {r['distance']:.4f}")
    except Exception as exc:
        logger.warning("Vector search failed: %s", exc)
        typer.echo("Vector search unavailable.")

    conn.close()
