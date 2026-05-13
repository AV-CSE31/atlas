"""Manifest management for the Atlas Knowledge Compiler.

The manifest (``raw/_manifest.json``) records the SHA-256 hash and source URL
of every ingested raw file.  It is used by the diff module to detect new or
changed files.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from .constants import RAW_MANIFEST_PATH

logger = logging.getLogger(__name__)


def get_manifest_path(base_path: Path) -> Path:
    """Return the absolute path to the raw manifest file.

    Args:
        base_path: Root directory of the Atlas knowledge base.

    Returns:
        Absolute :class:`~pathlib.Path` to ``raw/_manifest.json``.
    """
    return base_path / RAW_MANIFEST_PATH


def read_manifest(base_path: Path) -> dict:
    """Load the raw-file manifest from disk.

    Args:
        base_path: Root directory of the Atlas knowledge base.

    Returns:
        The manifest dictionary.  Returns ``{"files": {}}`` if the manifest
        does not exist yet or cannot be parsed.
    """
    manifest_path = get_manifest_path(base_path)
    if not manifest_path.exists():
        return {"files": {}}
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read manifest at %s: %s. Returning empty.", manifest_path, exc)
        return {"files": {}}


def write_manifest(base_path: Path, manifest: dict) -> None:
    """Persist *manifest* to disk.

    Args:
        base_path: Root directory of the Atlas knowledge base.
        manifest: The manifest dictionary to write.
    """
    manifest_path = get_manifest_path(base_path)
    try:
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
    except OSError as exc:
        logger.error("Failed to write manifest to %s: %s", manifest_path, exc)
        raise


def calculate_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content*.

    Args:
        content: The text content to hash (encoded as UTF-8 before hashing).

    Returns:
        A 64-character lowercase hexadecimal string.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def update_manifest(
    base_path: Path,
    raw_path: str,
    content: str,
    source_url: str | None = None,
) -> None:
    """Add or update a file entry in the manifest.

    Args:
        base_path: Root directory of the Atlas knowledge base.
        raw_path: Relative path of the raw file (as stored in ``raw/``).
        content: The raw text content of the file (used to compute the hash).
        source_url: Original URL or path the content was ingested from.
    """
    manifest = read_manifest(base_path)
    file_hash = calculate_hash(content)
    manifest["files"][raw_path] = {
        "hash": file_hash,
        "source": source_url or raw_path,
    }
    write_manifest(base_path, manifest)
