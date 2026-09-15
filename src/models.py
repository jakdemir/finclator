"""Model registry: which classifier's predictions drive the matrix.

Every call is tagged with the model that produced it; trust, matrix, Pine history and the audit page are all
computed per model. `active_model()` selects which one is *published* (matrix.json, tradingview/, audit.html).
"""
from __future__ import annotations

import os
import sqlite3

# Interactive Fable labels from the initial backfill session.
BACKFILL_MODEL = "claude-fable-5.1/interactive"


def active_model() -> str:
    """Model whose predictions are published. FINCLATOR_ACTIVE_MODEL overrides; default = classifier MODEL."""
    return os.environ.get("FINCLATOR_ACTIVE_MODEL") or os.environ.get("FINCLATOR_MODEL") or BACKFILL_MODEL


def list_models(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT model FROM calls ORDER BY model")]
