"""Compiler agent for the Atlas Knowledge Compiler.

Iterates over pending raw files identified by the diff module, sends each
through the LLM extraction pipeline, and writes/updates wiki article files.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
import yaml

from .constants import (
    DEFAULT_IMPORTANCE,
    DEFAULT_MATURITY,
    WIKI_DOMAINS_PATH,
)
from .diff import get_compiled_state, get_pending_files, save_compiled_state
from .llm import Concept, Relationship, extract_knowledge, get_compiler_model
from .manifest import read_manifest
from .utils import atomic_write, sanitize_filename

logger = logging.getLogger(__name__)


def create_wiki_article(
    base_path: Path,
    concept: Concept,
    source_rel_path: str,
    relationships: list[Relationship],
) -> None:
    """Create or update a wiki article for *concept*.

    If the article file already exists a new context section is appended;
    otherwise a full article with YAML front-matter is created.  All file
    writes use :func:`~atlas.utils.atomic_write` to prevent partial updates.

    Args:
        base_path: Root directory of the Atlas knowledge base.
        concept: The :class:`~atlas.llm.Concept` to create an article for.
        source_rel_path: Relative path of the source raw document (used for
            wikilink attribution).
        relationships: Full list of relationships extracted from the same
            document; those involving *concept* are included in the article.
    """
    filename = f"{sanitize_filename(concept.name)}.md"
    article_path = base_path / WIKI_DOMAINS_PATH / filename

    if article_path.exists():
        with open(article_path, "r", encoding="utf-8") as fh:
            existing = fh.read()
        new_section = (
            f"\n## New context from [[{source_rel_path}]]\n"
            f"Definition updated: {concept.definition}\n"
        )
        atomic_write(article_path, existing + new_section)
    else:
        fm: dict = {
            "title": concept.name,
            "aliases": concept.aliases,
            "sources": [source_rel_path],
            "importance": DEFAULT_IMPORTANCE,
            "maturity": DEFAULT_MATURITY,
        }
        fm_str = yaml.dump(fm, default_flow_style=False)

        rel_md = ""
        concept_lower = concept.name.lower()
        relevant_rels = [
            r
            for r in relationships
            if r.from_concept.lower() == concept_lower
            or r.to_concept.lower() == concept_lower
        ]
        if relevant_rels:
            rel_md = "## Relationships\n"
            for r in relevant_rels:
                rel_md += (
                    f"- **{r.relation_type}**: [[{r.to_concept}]] "
                    f"(Evidence: {r.evidence})\n"
                )

        content = f"---\n{fm_str}---\n\n# {concept.name}\n\n{concept.definition}\n\n{rel_md}\n"
        article_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(article_path, content)


def compile_cmd(incremental: bool = True, base_path: Path = Path(".")) -> None:
    """Run the compiler agent over all pending raw files.

    Reads the manifest to identify new or changed source documents, runs each
    through LLM knowledge extraction, writes wiki articles, and checkpoints
    the compiled state after each file so that partial runs are resumable.

    Args:
        incremental: When ``True`` (default) only files whose content hash
            has changed since the last run are processed.  Pass ``False`` to
            recompile everything from scratch.
        base_path: Root directory of the Atlas knowledge base.
    """
    typer.echo("Starting compilation...")
    if not incremental:
        save_compiled_state(base_path, {})

    pending = get_pending_files(base_path)
    if not pending:
        typer.echo("No files to compile.")
        return

    manifest = read_manifest(base_path)
    state = get_compiled_state(base_path)
    model = get_compiler_model(base_path)

    for rel_path in pending:
        typer.echo(f" - Processing {rel_path}")
        full_path = base_path / rel_path
        try:
            with open(full_path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            logger.error("Cannot read source file %s: %s", full_path, exc)
            typer.echo(f"   Skipping {rel_path}: unable to read file.")
            continue

        output = extract_knowledge(content, model)
        for concept in output.concepts:
            try:
                create_wiki_article(base_path, concept, rel_path, output.relationships)
            except Exception as exc:
                logger.error("Failed to write article for concept '%s': %s", concept.name, exc)

        file_hash = manifest["files"][rel_path]["hash"]
        state[rel_path] = file_hash
        save_compiled_state(base_path, state)

    typer.echo("Compilation complete.")
