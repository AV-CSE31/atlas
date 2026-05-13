"""Source parsers for the Atlas Knowledge Compiler.

Provides functions to fetch and normalise content from URLs (via the Jina
Reader API) and local files (PDF via pymupdf4llm, plain text fallback).
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def extract_title_from_md(content: str) -> str | None:
    """Return the first H1 heading found in *content*, or ``None``.

    Args:
        content: Markdown or plain-text content to scan for a title.

    Returns:
        The text of the first ``# Heading`` line, or ``None`` if no H1 exists.
    """
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def parse_url(url: str) -> tuple[str, str]:
    """Fetch a web page via the Jina Reader API and return (title, markdown).

    Args:
        url: A fully-qualified HTTP/HTTPS URL to fetch.

    Returns:
        A ``(title, content)`` tuple where *title* is extracted from the first
        H1 heading and *content* is the raw Jina Reader markdown response.

    Raises:
        requests.HTTPError: If the Jina Reader API returns a non-2xx response.
        ValueError: If *url* is not a valid HTTP/HTTPS URL.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url!r}")

    jina_url = f"https://r.jina.ai/{url}"
    response = requests.get(jina_url, timeout=30)
    response.raise_for_status()
    content = response.text
    title = extract_title_from_md(content) or url
    return title, content


def parse_pdf(file_path: Path) -> tuple[str, str]:
    """Parse a local PDF into markdown using pymupdf4llm.

    Args:
        file_path: Absolute or relative path to a PDF file.

    Returns:
        A ``(title, content)`` tuple where *title* is extracted from the first
        H1 heading and *content* is the pymupdf4llm markdown output.
    """
    import pymupdf4llm  # lazy import — optional dependency

    md_text: str = pymupdf4llm.to_markdown(str(file_path))
    title = extract_title_from_md(md_text) or file_path.stem
    return title, md_text


def parse_fallback(file_path: Path) -> tuple[str, str]:
    """Read a plain-text or markdown file as-is.

    Args:
        file_path: Path to a text-like file (e.g. ``.md``, ``.txt``).

    Returns:
        A ``(title, content)`` tuple.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    title = extract_title_from_md(content) or file_path.stem
    return title, content


def ingest_source(source: str) -> tuple[str, str, str]:
    """Dispatch *source* to the appropriate parser and return normalised content.

    Args:
        source: A URL string or local file path.

    Returns:
        A ``(source_type, title, markdown_content)`` triple where *source_type*
        is one of ``"article"`` or ``"paper"``.

    Raises:
        ValueError: If the source path does not exist.
    """
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        title, content = parse_url(source)
        return "article", title, content

    path = Path(source)
    if not path.exists():
        raise ValueError(f"Source not found: {source}")

    if path.suffix.lower() == ".pdf":
        title, content = parse_pdf(path)
        return "paper", title, content

    title, content = parse_fallback(path)
    return "article", title, content
