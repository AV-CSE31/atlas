"""Ingest command for the Atlas Knowledge Compiler.

Accepts a URL or local file path, converts it to markdown via the appropriate
parser, writes the result to ``raw/``, and records it in the manifest.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
import yaml

from .manifest import update_manifest
from .parsers import ingest_source
from .utils import atomic_write, sanitize_filename

logger = logging.getLogger(__name__)


def ingest_cmd(source: str, base_path: Path = Path(".")) -> None:
    """Ingest a source URL or file into the raw directory.

    Converts the source to normalised markdown, writes it to the appropriate
    sub-directory of ``raw/`` (``articles/``, ``papers/``, etc.), and updates
    the manifest with the file's SHA-256 hash.

    Args:
        source: A URL (``http://`` or ``https://``) or an absolute/relative
            local file path to a PDF or markdown file.
        base_path: Root directory of the Atlas knowledge base.

    Raises:
        typer.Exit: If the source cannot be ingested.
    """
    typer.echo(f"Ingesting: {source}...")

    try:
        source_type, title, content = ingest_source(source)
    except Exception as exc:
        logger.error("Failed to ingest %s: %s", source, exc)
        typer.echo(f"Failed to ingest {source}: {exc}", err=True)
        raise typer.Exit(1)

    if not title:
        title = "Untitled Document"

    filename = f"{sanitize_filename(title)}.md"
    type_dir = base_path / "raw" / f"{source_type}s"
    type_dir.mkdir(parents=True, exist_ok=True)

    output_path = type_dir / filename
    frontmatter: dict = {"title": title, "source": source}
    fm_str = yaml.dump(frontmatter, default_flow_style=False)
    final_content = f"---\n{fm_str}---\n\n{content}"

    atomic_write(output_path, final_content)

    rel_path = str(output_path.relative_to(base_path)).replace("\\", "/")
    update_manifest(base_path, rel_path, content, source)
    typer.echo(f"Successfully ingested to {rel_path}")
