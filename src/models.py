"""Model registry: which classifier's predictions drive the matrix.

Every call is tagged with the model that produced it; trust, matrix, Pine history and the audit page are all
computed per model. `active_model()` selects which one is *published* (matrix.json, tradingview/, audit.html).
"""
from __future__ import annotations

import os
import sqlite3

# The one default text classifier: local Qwen3.6 registered in Ollama from ~/.hermes/models (see AGENTS.md).
DEFAULT_MODEL = "qwen3.6-local:35b-a3b-q4_K_M"
DEFAULT_BASE_URL = "http://localhost:11434/v1"

# Stage 2a gate (src/gate.py): Jev decides is_call for NEW tweets, the text model labels only those that pass.
# Labels stay under the text model's own tag (the backlog was labeled ungated; the gate only saves GPU going forward).
# FINCLATOR_GATE=0 disables it; FINCLATOR_GATE_TAG=1 stores gated labels under "<model>+jev" as a separate dimension.
GATE_SUFFIX = "+jev"
GATE_ON = os.environ.get("FINCLATOR_GATE", "1") == "1"
GATE_TAG = os.environ.get("FINCLATOR_GATE_TAG", "0") == "1"

# Interactive Fable labels from the initial backfill session (kept as a second model dimension).
BACKFILL_MODEL = "claude-fable-5.1/interactive"


def text_model() -> str:
    """The text model that produces quote / price_target / labels (FINCLATOR_MODEL overrides)."""
    return os.environ.get("FINCLATOR_MODEL") or DEFAULT_MODEL


def classifier_model() -> str:
    """Tag new classifications are stored under: the text model (plus "+jev" only when FINCLATOR_GATE_TAG=1)."""
    m = text_model()
    return m + GATE_SUFFIX if GATE_ON and GATE_TAG and not m.endswith(GATE_SUFFIX) else m


def base_model(model: str) -> str:
    """Strip the gate suffix: the text-model dimension a hybrid tag was derived from."""
    return model[:-len(GATE_SUFFIX)] if model.endswith(GATE_SUFFIX) else model


def classifier_base_url() -> str | None:
    """OpenAI/Ollama endpoint for the classifier; None → Anthropic API (claude-* models only)."""
    if "FINCLATOR_MODEL_BASE_URL" in os.environ:
        return os.environ["FINCLATOR_MODEL_BASE_URL"] or None
    return None if text_model().startswith("claude-") else DEFAULT_BASE_URL


def active_model() -> str:
    """Model whose predictions are published. FINCLATOR_ACTIVE_MODEL overrides; default = classifier model."""
    return os.environ.get("FINCLATOR_ACTIVE_MODEL") or classifier_model()


def list_models(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT model FROM calls ORDER BY model")]
