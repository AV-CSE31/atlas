"""Smoke tests for atlas.constants — verifies all expected symbols exist."""

from __future__ import annotations

import atlas.constants as C


def test_embedding_dim_positive() -> None:
    assert C.EMBEDDING_DIM > 0


def test_llm_content_limit_gt_embedding_limit() -> None:
    assert C.LLM_CONTENT_CHAR_LIMIT > C.EMBEDDING_CONTENT_CHAR_LIMIT


def test_default_maturity_is_string() -> None:
    assert isinstance(C.DEFAULT_MATURITY, str)


def test_archive_threshold_reasonable() -> None:
    assert 0 < C.ARCHIVE_SCORE_THRESHOLD < 100


def test_recency_decay_positive() -> None:
    assert C.RECENCY_DECAY_DAYS > 0


def test_max_query_length_positive() -> None:
    assert C.MAX_QUERY_LENGTH > 0


def test_sentinel_is_nonempty_string() -> None:
    assert isinstance(C.DOCUMENT_INJECTION_SENTINEL, str)
    assert len(C.DOCUMENT_INJECTION_SENTINEL) > 0
