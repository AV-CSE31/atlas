"""Shared embedding utilities for the Atlas Knowledge Compiler.

Centralises the ``get_embedding()`` helper so that ``index_cmd``, ``search``,
and ``server`` all use a single, well-tested implementation rather than
separate copies.
"""

from __future__ import annotations

import logging

import litellm

from .constants import EMBEDDING_CONTENT_CHAR_LIMIT, EMBEDDING_DIM, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    """Return a float vector embedding for *text* using LiteLLM.

    Truncates the input to :data:`~atlas.constants.EMBEDDING_CONTENT_CHAR_LIMIT`
    characters before sending the request.  On failure, logs a warning and
    returns a zero vector of length :data:`~atlas.constants.EMBEDDING_DIM`
    so callers can continue without crashing.

    Args:
        text: The text to embed.
        model: The LiteLLM model identifier (default: ``text-embedding-3-small``).

    Returns:
        A list of floats representing the embedding.  Falls back to a zero
        vector of dimension :data:`~atlas.constants.EMBEDDING_DIM` on error.
    """
    truncated = text[:EMBEDDING_CONTENT_CHAR_LIMIT]
    try:
        response = litellm.embedding(model=model, input=[truncated])
        return response.data[0]["embedding"]
    except Exception as exc:
        logger.warning(
            "Embedding request failed for model=%s: %s. Returning zero vector.",
            model,
            exc,
        )
        return [0.0] * EMBEDDING_DIM
