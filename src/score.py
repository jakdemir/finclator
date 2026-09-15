"""Trust scores with sample-size shrinkage.

score = (hits + PRIOR_N * 0.5) / (n + PRIOR_N), hits = CORRECT + 0.5*PARTIAL, then ±TARGET_BONUS if the
call carried an explicit price target that was hit / missed (a stated level is a stronger, more falsifiable claim).
With PRIOR_N=10, one lucky call moves you from 0.50 to 0.545, not to 1.0.
Computed per (handle, asset, horizon), per (handle, asset, *), and (handle, *, *).

Point-in-time: `as_of` restricts to outcomes whose exit_date <= as_of, so historical matrices have no lookahead.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from .db import connect

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


def compute(conn: sqlite3.Connection, as_of: date | None = None) -> dict[tuple[str, str, str], tuple[int, float, float]]:
    """{(handle, asset, horizon): (n, hits, score)} using outcomes matured on/before as_of."""
    q = """SELECT c.handle, c.asset, c.horizon, o.result, o.target_hit
           FROM outcomes o JOIN calls c ON c.id = o.call_id"""
    args: tuple = ()
    if as_of:
        q += " WHERE o.exit_date <= ?"
        args = (as_of.isoformat(),)
    agg: dict[tuple[str, str, str], list[float]] = {}
    for r in conn.execute(q, args):
        h = _hit(r["result"], r["target_hit"])
        for key in ((r["handle"], r["asset"], r["horizon"]), (r["handle"], r["asset"], "*"), (r["handle"], "*", "*")):
            agg.setdefault(key, []).append(h)
    return {k: (len(v), sum(v), _score(len(v), sum(v))) for k, v in agg.items()}


def recompute(conn: sqlite3.Connection) -> int:
    scores = compute(conn)
    conn.execute("DELETE FROM trust")
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany("INSERT INTO trust(handle, asset, horizon, n, correct, score, computed_at) VALUES(?,?,?,?,?,?,?)",
                     [(h, a, hz, n, hits, s, now) for (h, a, hz), (n, hits, s) in scores.items()])
    conn.commit()
    return len(scores)


class TrustLookup:
    """Point-in-time trust lookup with the specific→asset→overall→prior fallback."""

    def __init__(self, conn: sqlite3.Connection, as_of: date | None = None):
        self.scores = compute(conn, as_of)

    def get(self, handle: str, asset: str, horizon: str) -> float:
        for a, h in ((asset, horizon), (asset, "*"), ("*", "*")):
            r = self.scores.get((handle, a, h))
            if r:
                return r[2]
        return 0.5


def trust_for(conn: sqlite3.Connection, handle: str, asset: str, horizon: str) -> float:
    """Current trust from the `trust` table (specific → asset → overall → prior 0.5)."""
    for a, h in ((asset, horizon), (asset, "*"), ("*", "*")):
        r = conn.execute("SELECT score FROM trust WHERE handle=? AND asset=? AND horizon=?", (handle, a, h)).fetchone()
        if r:
            return r["score"]
    return 0.5


if __name__ == "__main__":
    conn = connect()
    print(recompute(conn), "trust rows")
    for r in conn.execute("SELECT handle, asset, horizon, n, round(correct,1), round(score,3) FROM trust ORDER BY handle, asset, horizon"):
        print(tuple(r))
