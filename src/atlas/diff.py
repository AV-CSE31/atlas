"""Diff module for the Atlas Knowledge Compiler.

Compares the raw-file manifest against the compiled-state checkpoint to
identify files that need to be (re-)compiled.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from .constants import COMPILED_STATE_PATH

logger = logging.getLogger(__name__)


def get_compiled_state(base_path: Path) -> dict[str, str]:
    """Load the incremental compilation state from disk.

    Args:
        base_path: Root directory of the Atlas knowledge base.

    Returns:
        A mapping of ``{rel_path: sha256_hash}`` for files already compiled.
        Returns an empty dict if the state file does not exist.
    """
    state_path = base_path / COMPILED_STATE_PATH
    if not state_path.exists():
        return {}
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read compiled state from %s: %s. Treating as empty.", state_path, exc)
        return {}


def save_compiled_state(base_path: Path, state: dict[str, str]) -> None:
    """Persist *state* to the compiled-state checkpoint file.

    Args:
        base_path: Root directory of the Atlas knowledge base.
        state: Mapping of ``{rel_path: sha256_hash}`` to persist.
    """
    state_path = base_path / COMPILED_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
    except OSError as exc:
        logger.error("Failed to save compiled state: %s", exc)


def get_pending_files(base_path: Path) -> list[str]:
    """Return relative paths of raw files that need compilation.

    A file is considered pending if it is absent from the compiled-state
    checkpoint or if its recorded hash differs from the manifest hash (i.e.
    the file has been modified since it was last compiled).

    Args:
        base_path: Root directory of the Atlas knowledge base.

    Returns:
        A list of relative path strings for files pending compilation.
    """
    from .manifest import read_manifest

    manifest = read_manifest(base_path)
    compiled_state = get_compiled_state(base_path)

    pending: list[str] = []
    for rel_path, data in manifest.get("files", {}).items():
        file_hash = data.get("hash")
        if rel_path not in compiled_state or compiled_state[rel_path] != file_hash:
            pending.append(rel_path)
    return pending


def diff_cmd(base_path: Path = Path(".")) -> None:
    """Print the list of raw files pending compilation.

    Args:
        base_path: Root directory of the Atlas knowledge base.
    """
    pending = get_pending_files(base_path)
    if not pending:
        typer.echo("No pending changes.")
        return
    typer.echo(f"Found {len(pending)} pending file(s):")
    for f in pending:
        typer.echo(f" - {f}")
