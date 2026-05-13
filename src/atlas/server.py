"""MCP server for the Atlas Knowledge Compiler.

Exposes two MCP tools — ``wiki_search`` and ``wiki_read`` — allowing external
clients (Claude Desktop, Cursor, VS Code) to query the compiled knowledge base
via the Model Context Protocol.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from mcp.server.fastmcp import FastMCP

from .constants import MAX_QUERY_LENGTH, SEARCH_RESULT_LIMIT
from .db import get_db_connection

logger = logging.getLogger(__name__)


def serve_cmd(base_path: Path = Path(".")) -> None:
    """Launch the Atlas MCP server in stdio transport mode.

    Registers ``wiki_search`` and ``wiki_read`` as MCP tools and blocks until
    the transport is closed by the client.

    Args:
        base_path: Root directory of the Atlas knowledge base.
    """
    mcp = FastMCP("Atlas Knowledge Base")
    _resolved_base = base_path.resolve()

    @mcp.tool()
    def wiki_search(query: str) -> str:
        """Search wiki articles by keyword using FTS5.

        Args:
            query: The search query (max 1 000 characters).

        Returns:
            A formatted string listing matching article titles, paths, and
            snippets, or an error/empty-result message.
        """
        query = query.strip()
        if not query:
            return "Error: query must not be empty."
        if len(query) > MAX_QUERY_LENGTH:
            return f"Error: query exceeds maximum length of {MAX_QUERY_LENGTH} characters."

        db_path = _resolved_base / "atlas.db"
        try:
            conn = get_db_connection(db_path)
        except Exception as exc:
            logger.error("Cannot open atlas.db: %s", exc)
            return f"Error: could not open the knowledge base database: {exc}"

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, path, "
                "snippet(articles_fts, 1, '[', ']', '...', 10) as snip "
                "FROM articles_fts WHERE articles_fts MATCH ? ORDER BY rank "
                f"LIMIT {SEARCH_RESULT_LIMIT}",
                (query,),
            )
            rows = cursor.fetchall()
        except Exception as exc:
            logger.error("FTS search error: %s", exc)
            return f"Error: search failed: {exc}"
        finally:
            conn.close()

        if not rows:
            return "No matches found."

        result = "Found the following articles:\n"
        for r in rows:
            result += f"- **{r['title']}** ({r['path']}): {r['snip']}\n"
        return result

    @mcp.tool()
    def wiki_read(path: str) -> str:
        """Read a wiki article by its relative path.

        The path must resolve to a file within the knowledge base directory.
        Any attempt to traverse outside (e.g. ``../../etc/passwd``) is rejected.

        Args:
            path: Relative path to a wiki article (e.g. ``wiki/domains/foo.md``).

        Returns:
            The raw markdown content of the article, or an error message.
        """
        try:
            requested = (_resolved_base / path).resolve()
        except Exception as exc:
            logger.warning("Path resolution failed for input %r: %s", path, exc)
            return "Error: invalid path."

        # Prevent path traversal — the resolved path must stay inside base_path
        try:
            requested.relative_to(_resolved_base)
        except ValueError:
            logger.warning(
                "Path traversal attempt blocked: requested=%s base=%s",
                requested,
                _resolved_base,
            )
            return "Error: access denied."

        if not requested.exists():
            return f"Error: file not found at {path}"

        try:
            with open(requested, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            logger.error("Could not read %s: %s", requested, exc)
            return f"Error: could not read file: {exc}"

    typer.echo("Starting Atlas MCP server (stdio)...")
    mcp.run(transport="stdio")
