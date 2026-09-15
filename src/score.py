"""Trust scores with sample-size shrinkage — computed per classifier model.

score = (hits + PRIOR_N * 0.5) / (n + PRIOR_N), hits = CORRECT + 0.5*PARTIAL, then ±TARGET_BONUS if the
call carried an explicit price target that was hit / missed (a stated level is a stronger, more falsifiable claim).
With PRIOR_N=10, one lucky call moves you from 0.50 to 0.545, not to 1.0.
Computed per (model, handle, asset, horizon), per (model, handle, asset, *), and (model, handle, *, *).

Point-in-time: `as_of` restricts to outcomes whose exit_date <= as_of, so historical matrices have no lookahead.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from .db import connect
from .models import active_model, list_models

PRIOR_N = 10
HIT = {"CORRECT": 1.0, "PARTIAL": 0.5, "WRONG": 0.0}
TARGET_BONUS = 0.25  # hit → +0.25, miss → -0.25 (clamped to [0, 1])


def _score(n: int, hits: float) -> float:
    return (hits + PRIOR_N * 0.5) / (n + PRIOR_N)


def _hit(result: str, target_hit: int | None) -> float:
    h = HIT[result]
    if target_hit is not None:
        h = min(1.0, max(0.0, h + (TARGET_BONUS if target_hit else -TARGET_BONUS)))
    return h


def compute(conn: sqlite3.Connection, model: str, as_of: date | None = None) -> dict[tuple[str, str, str], tuple[int, float, float]]:
    """{(handle, asset, horizon): (n, hits, score)} for one model, using outcomes matured on/before as_of."""
    q = """SELECT c.handle, c.asset, c.horizon, o.result, o.target_hit
           FROM outcomes o JOIN calls c ON c.id = o.call_id WHERE c.model = ?"""
    args: tuple = (model,)
    if as_of:
        q += " AND o.exit_date <= ?"
        args += (as_of.isoformat(),)
    agg: dict[tuple[str, str, str], list[float]] = {}
    for r in conn.execute(q, args):
        h = _hit(r["result"], r["target_hit"])
        for key in ((r["handle"], r["asset"], r["horizon"]), (r["handle"], r["asset"], "*"), (r["handle"], "*", "*")):
            agg.setdefault(key, []).append(h)
    return {k: (len(v), sum(v), _score(len(v), sum(v))) for k, v in agg.items()}


def recompute(conn: sqlite3.Connection) -> int:
    """Recompute trust for every model that has calls."""
    conn.execute("DELETE FROM trust")
    now = datetime.now(timezone.utc).isoformat()
    total = 0
    for model in list_models(conn):
        scores = compute(conn, model)
        conn.executemany(
            "INSERT INTO trust(model, handle, asset, horizon, n, correct, score, computed_at) VALUES(?,?,?,?,?,?,?,?)",
            [(model, h, a, hz, n, hits, s, now) for (h, a, hz), (n, hits, s) in scores.items()])
        total += len(scores)
    conn.commit()
    return total


class TrustLookup:
    """Point-in-time trust lookup for one model with the specific→asset→overall→prior fallback."""

    def __init__(self, conn: sqlite3.Connection, model: str | None = None, as_of: date | None = None):
        self.model = model or active_model()
        self.scores = compute(conn, self.model, as_of)

    def get(self, handle: str, asset: str, horizon: str) -> float:
        for a, h in ((asset, horizon), (asset, "*"), ("*", "*")):
            r = self.scores.get((handle, a, h))
            if r:
                return r[2]
        return 0.5


if __name__ == "__main__":
    conn = connect()
    print(recompute(conn), "trust rows")
    for r in conn.execute("SELECT model, handle, asset, horizon, n, round(correct,1), round(score,3) FROM trust ORDER BY 1,2,3,4"):
        print(tuple(r))
