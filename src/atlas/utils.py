"""Shared utility helpers for the Atlas Knowledge Compiler.

This module contains small, dependency-free helper functions that are reused
across multiple Atlas modules (e.g. filename sanitisation, atomic file I/O).
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """Convert an arbitrary string into a safe, lower-cased filename stem.

    Removes all characters that are not word characters, spaces, or hyphens,
    collapses consecutive separators, and strips leading/trailing whitespace.

    Args:
        name: The raw string to sanitise (e.g. a concept name or article title).

    Returns:
        A lower-cased, hyphen-separated filename stem suitable for use with
        ``.md`` article files inside the wiki directory.

    Examples:
        >>> sanitize_filename("Graph RAG: Community Summaries!")
        'graph-rag-community-summaries'
    """
    cleaned = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "-", cleaned)


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* atomically using a temp-file-then-rename strategy.

    This prevents partial writes from corrupting existing files when an error
    occurs mid-write (power loss, KeyboardInterrupt, disk-full, etc.).

    Args:
        path: Destination file path.  The parent directory must already exist.
        content: Text to write.
        encoding: Character encoding for the output file (default ``utf-8``).
    """
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=path.parent,
            encoding=encoding,
            delete=False,
            suffix=".tmp",
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        shutil.move(tmp_path, path)
    except Exception:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        raise
