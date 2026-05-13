"""LLM interaction layer for the Atlas Knowledge Compiler.

Defines the Pydantic output schema for knowledge extraction and the
``extract_knowledge()`` function that calls the configured LLM via LiteLLM.
"""

from __future__ import annotations

import json
import logging

import litellm
from pydantic import BaseModel

from .constants import (
    CONFIG_PATH,
    DOCUMENT_INJECTION_SENTINEL,
    LLM_CONTENT_CHAR_LIMIT,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------


class Concept(BaseModel):
    """A named concept extracted from a document."""

    name: str
    definition: str
    aliases: list[str]


class Relationship(BaseModel):
    """A directional relationship between two concepts."""

    from_concept: str
    to_concept: str
    relation_type: str
    evidence: str


class ExtractionOutput(BaseModel):
    """Structured output produced by the compiler LLM for a single document."""

    concepts: list[Concept]
    relationships: list[Relationship]
    claims: list[str]
    questions: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_compiler_model(base_path: "Path") -> str:  # noqa: F821 — forward ref only
    """Read the configured compiler model name from ``.atlas/config.yaml``.

    Args:
        base_path: Root directory of the Atlas knowledge base.

    Returns:
        The LiteLLM model identifier string.  Falls back to
        ``gemini/gemini-2.5-flash`` if the key is absent.
    """
    import yaml
    from pathlib import Path

    config_path = Path(base_path) / CONFIG_PATH
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        return config.get("llm", {}).get("compiler_model", "gemini/gemini-2.5-flash")
    except OSError as exc:
        logger.warning("Could not read config at %s: %s. Using default model.", config_path, exc)
        return "gemini/gemini-2.5-flash"


def extract_knowledge(content: str, model: str) -> ExtractionOutput:
    """Extract concepts, relationships, claims and open questions from *content*.

    The document text is truncated to :data:`~atlas.constants.LLM_CONTENT_CHAR_LIMIT`
    characters and wrapped in an injection-defence sentinel before being sent
    to the LLM.  On failure an empty :class:`ExtractionOutput` is returned and
    the error is logged.

    Args:
        content: Raw markdown or plain-text content of a source document.
        model: LiteLLM model identifier for the compiler agent.

    Returns:
        An :class:`ExtractionOutput` with extracted knowledge, or an empty
        instance if the LLM call or JSON parsing fails.
    """
    safe_content = f"{DOCUMENT_INJECTION_SENTINEL}\n{content[:LLM_CONTENT_CHAR_LIMIT]}"
    prompt = (
        "You are a knowledge compiler. Extract key concepts, relationships, "
        "claims, and open questions from the following document.\n"
        f"<document>\n{safe_content}\n</document>"
    )
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=ExtractionOutput,
            temperature=0.1,
        )
        json_str = response.choices[0].message.content
        data = json.loads(json_str)
        return ExtractionOutput(**data)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM JSON response: %s", exc)
    except Exception as exc:
        logger.error("LLM extraction failed for model=%s: %s", model, exc)
    return ExtractionOutput(concepts=[], relationships=[], claims=[], questions=[])
