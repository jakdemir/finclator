"""Model registry: which classifier's predictions drive the matrix.

Every call is tagged with the model that produced it; trust, matrix, Pine history and the audit page are all
computed per model. `active_model()` selects which one is *published* (matrix.json, tradingview/, audit.html).
"""
from __future__ import annotations

import os
import sqlite3

# The one default classifier: local Qwen3.6 registered in Ollama from ~/.hermes/models (see AGENTS.md).
DEFAULT_MODEL = "qwen3.6-local:35b-a3b-q4_K_M"
DEFAULT_BASE_URL = "http://localhost:11434/v1"

# Interactive Fable labels from the initial backfill session (kept as a second model dimension).
BACKFILL_MODEL = "claude-fable-5.1/interactive"


def classifier_model() -> str:
    """Model used for new classifications (FINCLATOR_MODEL overrides)."""
    return os.environ.get("FINCLATOR_MODEL") or DEFAULT_MODEL


def classifier_base_url() -> str | None:
    """OpenAI/Ollama endpoint for the classifier; None → Anthropic API (claude-* models only)."""
    if "FINCLATOR_MODEL_BASE_URL" in os.environ:
        return os.environ["FINCLATOR_MODEL_BASE_URL"] or None
    return None if classifier_model().startswith("claude-") else DEFAULT_BASE_URL


def active_model() -> str:
    """Model whose predictions are published. FINCLATOR_ACTIVE_MODEL overrides; default = classifier model."""
    return os.environ.get("FINCLATOR_ACTIVE_MODEL") or classifier_model()


def list_models(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT model FROM calls ORDER BY model")]
