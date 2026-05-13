"""Initialisation command for the Atlas Knowledge Compiler.

Creates the canonical directory structure, writes default configuration files,
and initialises the SQLite database schema.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer
import yaml

logger = logging.getLogger(__name__)

_DIRECTORIES = [
    "raw/papers",
    "raw/articles",
    "raw/repos",
    "raw/media",
    "wiki/domains",
    "wiki/connections",
    "wiki/_archived",
    "output/reports",
    "output/slides",
    "output/visualizations",
    ".atlas/cache",
]


def create_directory_structure(base_path: Path) -> None:
    """Create the canonical Atlas directory tree under *base_path*.

    Args:
        base_path: Root directory of the Atlas knowledge base.
    """
    for dir_path in _DIRECTORIES:
        full_path = base_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"Created directory: {dir_path}")


def init_kb(base_path: Path = Path(".")) -> None:
    """Initialise a new Atlas knowledge base in *base_path*.

    Creates the directory structure, a blank manifest, a default
    ``.atlas/config.yaml``, a ``kb.yaml`` descriptor, and the SQLite database.
    Existing files are not overwritten.

    Args:
        base_path: Root directory in which to initialise the knowledge base.
    """
    typer.echo("Initializing Atlas Knowledge Base...")

    create_directory_structure(base_path)

    # Empty manifest
    manifest_path = base_path / "raw/_manifest.json"
    if not manifest_path.exists():
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump({"files": {}}, fh, indent=2)
        typer.echo("Created raw/_manifest.json")

    # Compile log
    compile_log_path = base_path / ".atlas/compile.log"
    if not compile_log_path.exists():
        compile_log_path.touch()
        typer.echo("Created .atlas/compile.log")

    # Default config
    config_path = base_path / ".atlas/config.yaml"
    if not config_path.exists():
        default_config: dict = {
            "llm": {
                "compiler_model": "gemini/gemini-2.5-flash",
                "qa_model": "gemini/gemini-2.5-flash",
                "synthesis_model": "gemini/gemini-2.5-pro",
            },
            "akl": {
                "archive_threshold": 35,
            },
        }
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.dump(default_config, fh, default_flow_style=False)
        typer.echo("Created .atlas/config.yaml")

    # KB descriptor
    kb_yaml_path = base_path / "kb.yaml"
    if not kb_yaml_path.exists():
        default_kb: dict = {
            "name": "My Knowledge Base",
            "owner": "Atlas User",
        }
        with open(kb_yaml_path, "w", encoding="utf-8") as fh:
            yaml.dump(default_kb, fh, default_flow_style=False)
        typer.echo("Created kb.yaml")

    # SQLite database
    from .db import init_db

    init_db(base_path / "atlas.db")
    typer.echo("Initialized SQLite database: atlas.db")

    typer.echo("Initialization complete.")
