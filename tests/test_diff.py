"""Tests for atlas.diff — pending file detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.diff import get_compiled_state, get_pending_files, save_compiled_state
from atlas.manifest import update_manifest


@pytest.fixture()
def kb_root(tmp_path: Path) -> Path:
    (tmp_path / "raw").mkdir()
    (tmp_path / ".atlas").mkdir()
    return tmp_path


class TestGetCompiledState:
    def test_empty_when_no_file(self, kb_root: Path) -> None:
        assert get_compiled_state(kb_root) == {}

    def test_loads_existing_state(self, kb_root: Path) -> None:
        state = {"raw/articles/a.md": "deadbeef"}
        (kb_root / ".atlas/compiled_state.json").write_text(json.dumps(state))
        assert get_compiled_state(kb_root) == state

    def test_returns_empty_on_corrupt_json(self, kb_root: Path) -> None:
        (kb_root / ".atlas/compiled_state.json").write_text("CORRUPT")
        assert get_compiled_state(kb_root) == {}


class TestSaveCompiledState:
    def test_round_trip(self, kb_root: Path) -> None:
        state = {"raw/articles/z.md": "aabbcc"}
        save_compiled_state(kb_root, state)
        assert get_compiled_state(kb_root) == state


class TestGetPendingFiles:
    def test_new_file_is_pending(self, kb_root: Path) -> None:
        update_manifest(kb_root, "raw/articles/new.md", "hello world")
        pending = get_pending_files(kb_root)
        assert "raw/articles/new.md" in pending

    def test_compiled_file_not_pending(self, kb_root: Path) -> None:
        content = "compiled content"
        update_manifest(kb_root, "raw/articles/done.md", content)
        from atlas.manifest import calculate_hash
        save_compiled_state(kb_root, {"raw/articles/done.md": calculate_hash(content)})
        pending = get_pending_files(kb_root)
        assert "raw/articles/done.md" not in pending

    def test_modified_file_is_pending(self, kb_root: Path) -> None:
        update_manifest(kb_root, "raw/articles/mod.md", "new content")
        save_compiled_state(kb_root, {"raw/articles/mod.md": "old_hash"})
        pending = get_pending_files(kb_root)
        assert "raw/articles/mod.md" in pending

    def test_empty_manifest_gives_no_pending(self, kb_root: Path) -> None:
        assert get_pending_files(kb_root) == []
