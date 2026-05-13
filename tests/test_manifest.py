"""Tests for atlas.manifest — read/write/hash round-trips."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.manifest import calculate_hash, read_manifest, update_manifest, write_manifest


@pytest.fixture()
def kb_root(tmp_path: Path) -> Path:
    """Create a minimal KB directory structure under tmp_path."""
    (tmp_path / "raw").mkdir()
    return tmp_path


class TestCalculateHash:
    def test_deterministic(self) -> None:
        assert calculate_hash("hello") == calculate_hash("hello")

    def test_different_content_different_hash(self) -> None:
        assert calculate_hash("foo") != calculate_hash("bar")

    def test_returns_64_char_hex(self) -> None:
        h = calculate_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestReadManifest:
    def test_returns_empty_when_no_file(self, kb_root: Path) -> None:
        result = read_manifest(kb_root)
        assert result == {"files": {}}

    def test_reads_existing_manifest(self, kb_root: Path) -> None:
        manifest_path = kb_root / "raw/_manifest.json"
        manifest_path.write_text(json.dumps({"files": {"a.md": {"hash": "abc"}}}))
        result = read_manifest(kb_root)
        assert result["files"]["a.md"]["hash"] == "abc"

    def test_returns_empty_on_corrupt_json(self, kb_root: Path) -> None:
        (kb_root / "raw/_manifest.json").write_text("NOT JSON")
        result = read_manifest(kb_root)
        assert result == {"files": {}}


class TestWriteManifest:
    def test_round_trip(self, kb_root: Path) -> None:
        manifest = {"files": {"x.md": {"hash": "deadbeef", "source": "https://example.com"}}}
        write_manifest(kb_root, manifest)
        loaded = read_manifest(kb_root)
        assert loaded == manifest


class TestUpdateManifest:
    def test_adds_new_entry(self, kb_root: Path) -> None:
        update_manifest(kb_root, "raw/articles/foo.md", "some content", "https://example.com")
        manifest = read_manifest(kb_root)
        assert "raw/articles/foo.md" in manifest["files"]
        entry = manifest["files"]["raw/articles/foo.md"]
        assert entry["source"] == "https://example.com"
        assert entry["hash"] == calculate_hash("some content")

    def test_updates_existing_entry(self, kb_root: Path) -> None:
        update_manifest(kb_root, "raw/articles/foo.md", "v1")
        update_manifest(kb_root, "raw/articles/foo.md", "v2")
        manifest = read_manifest(kb_root)
        assert manifest["files"]["raw/articles/foo.md"]["hash"] == calculate_hash("v2")

    def test_source_defaults_to_path(self, kb_root: Path) -> None:
        update_manifest(kb_root, "raw/articles/bar.md", "content")
        manifest = read_manifest(kb_root)
        assert manifest["files"]["raw/articles/bar.md"]["source"] == "raw/articles/bar.md"
