"""Tests for atlas.utils — sanitize_filename and atomic_write."""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas.utils import atomic_write, sanitize_filename


class TestSanitizeFilename:
    def test_lowercases(self) -> None:
        assert sanitize_filename("Hello World") == "hello-world"

    def test_removes_special_chars(self) -> None:
        assert sanitize_filename("Graph RAG: Community!") == "graph-rag-community"

    def test_collapses_spaces_and_hyphens(self) -> None:
        assert sanitize_filename("foo  --  bar") == "foo-bar"

    def test_strips_leading_trailing(self) -> None:
        assert sanitize_filename("  concept  ") == "concept"

    def test_empty_string(self) -> None:
        assert sanitize_filename("") == ""

    def test_numbers_preserved(self) -> None:
        assert sanitize_filename("GPT-4o model 2024") == "gpt-4o-model-2024"


class TestAtomicWrite:
    def test_creates_file(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.md"
        atomic_write(dest, "# Title\n")
        assert dest.read_text(encoding="utf-8") == "# Title\n"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.md"
        dest.write_text("old content")
        atomic_write(dest, "new content")
        assert dest.read_text(encoding="utf-8") == "new content"

    def test_no_tmp_file_left_on_success(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.md"
        atomic_write(dest, "data")
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []
