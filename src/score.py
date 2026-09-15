"""Trust scores with sample-size shrinkage.

score = (hits + PRIOR_N * 0.5) / (n + PRIOR_N), hits = CORRECT + 0.5*PARTIAL.
With PRIOR_N=10, one lucky call moves you from 0.50 to 0.545, not to 1.0.
Computed per (handle, asset, horizon), per (handle, asset, *), and (handle, *, *).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .db import connect

PRIOR_N = 10
HIT = {"CORRECT": 1.0, "PARTIAL": 0.5, "WRONG": 0.0}


def _score(n: int, hits: float) -> float:
    return (hits + PRIOR_N * 0.5) / (n + PRIOR_N)


def recompute(conn: sqlite3.Connection) -> int:
    rows = conn.execute("""SELECT c.handle, c.asset, c.horizon, o.result
                           FROM outcomes o JOIN calls c ON c.id = o.call_id""").fetchall()
    agg: dict[tuple[str, str, str], list[float]] = {}
    for r in rows:
        h = HIT[r["result"]]
        for key in ((r["handle"], r["asset"], r["horizon"]), (r["handle"], r["asset"], "*"), (r["handle"], "*", "*")):
            agg.setdefault(key, []).append(h)
    conn.execute("DELETE FROM trust")
    now = datetime.now(timezone.utc).isoformat()
    for (handle, asset, horizon), hits in agg.items():
        conn.execute("INSERT INTO trust(handle, asset, horizon, n, correct, score, computed_at) VALUES(?,?,?,?,?,?,?)",
                     (handle, asset, horizon, len(hits), sum(hits), _score(len(hits), sum(hits)), now))
    conn.commit()
    return len(agg)


def trust_for(conn: sqlite3.Connection, handle: str, asset: str, horizon: str) -> float:
    """Most specific available score, falling back to asset-level, then overall, then prior 0.5."""
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
