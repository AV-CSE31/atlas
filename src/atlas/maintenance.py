"""Maintenance agent for the Atlas Knowledge Compiler.

Implements the Adaptive Knowledge Lifecycle (AKL) scoring algorithm and
archive logic.  Articles whose AKL score falls below the configured threshold
are moved from ``wiki/domains/`` to ``wiki/_archived/``.
"""

from __future__ import annotations

import logging
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import typer
import yaml

from .constants import (
    ARCHIVE_SCORE_THRESHOLD,
    CONFIG_PATH,
    DEFAULT_IMPORTANCE,
    RECENCY_DECAY_DAYS,
    WIKI_ARCHIVED_PATH,
    WIKI_DOMAINS_PATH,
)

logger = logging.getLogger(__name__)


def calculate_akl_score(importance: int, last_compiled_str: str) -> float:
    """Calculate the Adaptive Knowledge Lifecycle score for a wiki article.

    Score = importance × e^(−days_since_compiled / RECENCY_DECAY_DAYS)

    Args:
        importance: Integer importance weight (0–100).
        last_compiled_str: ISO-8601 datetime string for when the article was
            last compiled (typically stored in front-matter).

    Returns:
        A non-negative float representing the article's current AKL score.
        Returns ``importance`` (i.e. no decay) if the timestamp is unparseable.
    """
    try:
        last_comp = datetime.fromisoformat(last_compiled_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = max((now - last_comp).days, 0)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Could not parse last_compiled timestamp %r: %s — assuming 0 days elapsed.",
            last_compiled_str,
            exc,
        )
        days = 0

    recency = math.exp(-days / RECENCY_DECAY_DAYS)
    return importance * recency


def archive_cmd(base_path: Path = Path(".")) -> None:
    """Run the Maintenance Agent to archive stale wiki articles.

    Articles whose AKL score is below the threshold configured in
    ``.atlas/config.yaml`` (default: :data:`~atlas.constants.ARCHIVE_SCORE_THRESHOLD`)
    are moved to ``wiki/_archived/``.

    Args:
        base_path: Root directory of the Atlas knowledge base.
    """
    typer.echo("Running Maintenance Agent (Archival)...")

    threshold = ARCHIVE_SCORE_THRESHOLD
    config_path = base_path / CONFIG_PATH
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                config = yaml.safe_load(fh)
            threshold = config.get("akl", {}).get("archive_threshold", ARCHIVE_SCORE_THRESHOLD)
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("Could not read config at %s: %s. Using default threshold.", config_path, exc)

    domains_dir = base_path / WIKI_DOMAINS_PATH
    archived_dir = base_path / WIKI_ARCHIVED_PATH
    archived_dir.mkdir(parents=True, exist_ok=True)

    if not domains_dir.exists():
        typer.echo("No wiki/domains directory found — nothing to archive.")
        return

    archived_count = 0
    for file_path in domains_dir.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            logger.warning("Could not read %s: %s — skipping.", file_path, exc)
            continue

        importance: int = DEFAULT_IMPORTANCE
        last_compiled: str = datetime.now(timezone.utc).isoformat()

        if content.startswith("---"):
            end_fm = content.find("---", 3)
            if end_fm != -1:
                try:
                    fm = yaml.safe_load(content[3:end_fm])
                    importance = fm.get("importance", DEFAULT_IMPORTANCE)
                    last_compiled = fm.get("last_compiled", last_compiled)
                except yaml.YAMLError as exc:
                    logger.warning(
                        "YAML parse error in %s: %s — using default values.", file_path.name, exc
                    )

        score = calculate_akl_score(importance, last_compiled)
        if score < threshold:
            typer.echo(f"Archiving {file_path.name} (score: {score:.2f} < {threshold})")
            try:
                shutil.move(str(file_path), str(archived_dir / file_path.name))
                archived_count += 1
            except OSError as exc:
                logger.error("Failed to archive %s: %s", file_path.name, exc)

    typer.echo(f"Archived {archived_count} articles.")
