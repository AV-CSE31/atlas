"""Tests for atlas.parsers — title extraction and URL validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from atlas.parsers import extract_title_from_md, ingest_source, parse_fallback


class TestExtractTitleFromMd:
    def test_returns_first_h1(self) -> None:
        content = "Some preamble\n# My Title\n## Subtitle"
        assert extract_title_from_md(content) == "My Title"

    def test_returns_none_when_no_h1(self) -> None:
        assert extract_title_from_md("## Only H2\n\nParagraph.") is None

    def test_strips_whitespace(self) -> None:
        assert extract_title_from_md("#   Spaced   ") == "Spaced"

    def test_empty_string(self) -> None:
        assert extract_title_from_md("") is None


class TestParseFallback:
    def test_reads_markdown_file(self, tmp_path: Path) -> None:
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Hello\n\nWorld", encoding="utf-8")
        title, content = parse_fallback(md_file)
        assert title == "Hello"
        assert "World" in content

    def test_uses_stem_as_fallback_title(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "my-notes.txt"
        txt_file.write_text("No heading here.", encoding="utf-8")
        title, _ = parse_fallback(txt_file)
        assert title == "my-notes"


class TestIngestSource:
    def test_local_markdown_returns_article_type(self, tmp_path: Path) -> None:
        md_file = tmp_path / "note.md"
        md_file.write_text("# Note\n\nContent here.", encoding="utf-8")
        source_type, title, content = ingest_source(str(md_file))
        assert source_type == "article"
        assert title == "Note"

    def test_nonexistent_path_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Source not found"):
            ingest_source("/nonexistent/path/file.md")

    def test_url_dispatches_to_parse_url(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "# Fetched Title\n\nContent."
        mock_response.raise_for_status = MagicMock()
        with patch("atlas.parsers.requests.get", return_value=mock_response):
            source_type, title, content = ingest_source("https://example.com/article")
        assert source_type == "article"
        assert title == "Fetched Title"
        assert "Content." in content

    def test_invalid_url_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL"):
            from atlas.parsers import parse_url
            parse_url("ftp://not-http.example.com")
