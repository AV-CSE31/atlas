"""QA agent for the Atlas Knowledge Compiler.

Validates wikilink integrity across all articles in ``wiki/domains/``.
Reports broken ``[[wikilink]]`` references — i.e. links pointing to concept
files that do not exist on disk.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import typer

from .constants import WIKI_DOMAINS_PATH
from .utils import sanitize_filename

logger = logging.getLogger(__name__)

_WIKILINK_PATTERN = re.compile(r"\[\[(.*?)\]\]")


def get_all_concepts(base_path: Path) -> set[str]:
    """Return the set of all existing concept slugs (lowercase filename stems).

    Args:
        base_path: Root directory of the Atlas knowledge base.

    Returns:
        A :class:`set` of lower-cased file stems for every ``.md`` file in
        ``wiki/domains/``.
    """
    concepts: set[str] = set()
    domains_dir = base_path / WIKI_DOMAINS_PATH
    if not domains_dir.exists():
        return concepts
    for file_path in domains_dir.glob("*.md"):
        concepts.add(file_path.stem.lower())
    return concepts


def lint_cmd(base_path: Path = Path(".")) -> None:
    """Check all wiki articles for broken wikilinks.

    For every ``[[target]]`` reference found, the target is sanitised and
    checked against the set of known concept slugs.  A summary of any broken
    links is printed.

    Args:
        base_path: Root directory of the Atlas knowledge base.
    """
    typer.echo("Running QA Agent (Linting)...")
    domains_dir = base_path / WIKI_DOMAINS_PATH
    if not domains_dir.exists():
        typer.echo("No wiki/domains directory found — nothing to lint.")
        return

    valid_concepts = get_all_concepts(base_path)
    broken_links: list[tuple[str, str]] = []

    for file_path in domains_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            logger.warning("Could not read %s: %s — skipping.", file_path, exc)
            continue

        for match in _WIKILINK_PATTERN.finditer(content):
            target = match.group(1).strip()
            if sanitize_filename(target) not in valid_concepts:
                broken_links.append((file_path.name, target))

    if not broken_links:
        typer.echo("All wikilinks resolve correctly. Health OK.")
    else:
        typer.echo(f"Found {len(broken_links)} broken link(s):")
        for source_file, target in broken_links:
            typer.echo(f" - {source_file} -> [[{target}]]")
