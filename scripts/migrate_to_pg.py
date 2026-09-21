"""SQLite → Postgres migration. Streams every table with COPY, resets identity sequences, then verifies:
row counts, checksums per table, and an identical matrix.json built from each backend.

Usage: DATABASE_URL=postgres://… PYTHONPATH=. .venv/bin/python scripts/migrate_to_pg.py --yes
Rerunnable: --yes truncates the target tables first.
"""
from __future__ import annotations

import json
import os
import sys
import time

from src import db, matrix
from src.db import TABLES

CHUNK = 5000


def _copy_table(src, pg, table: str) -> int:
    cols = db.columns(src, table)
    raw = pg.raw
    n = 0
    cur = src.execute(f"SELECT {', '.join(cols)} FROM {table}")
    with raw.cursor() as c, c.copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as cp:
        while True:
            rows = cur.fetchmany(CHUNK)
            if not rows:
                break
            for r in rows:
                cp.write_row(tuple(r))
            n += len(rows)
            print(f"  {table}: {n:,}", end="\r", flush=True)
    raw.commit()
    print(f"  {table}: {n:,} rows   ")
    return n


def _checksum(conn, table: str) -> tuple:
    """Backend-agnostic fingerprint: count + a few numeric/text aggregates on stable columns."""
    cols = db.columns(conn, table)
    is_pg = getattr(conn, "backend", "sqlite") == "postgres"
    agg = ["count(*)"]
    for c in cols:
        if c in ("confidence", "close", "return_pct", "score", "correct", "n", "price_target", "entry_close"):
            agg.append(f"round(cast(sum({c}) as numeric), 4)" if is_pg else f"round(sum({c}), 4)")
        elif c in ("id", "call_id") and table in ("calls", "outcomes"):
            agg.append(f"sum({c})")
        elif c in ("id", "tweet_id", "handle", "model", "asset", "date", "called_at", "result", "text"):
            agg.append(f"sum(length({c}))")
    r = conn.execute(f"SELECT {', '.join(agg)} FROM {table}").fetchone()
    return tuple(float(x) if x is not None else None for x in r)


def main() -> int:
    yes = "--yes" in sys.argv
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    src = db.connect_sqlite()
    pg = db.connect(url=url)
    print("source:", db.DB_PATH, "| target:", url.split("@")[-1].split("?")[0])

    if not yes:
        print("dry run — add --yes to migrate")
        return 0
    t0 = time.time()
    pg.execute("TRUNCATE " + ", ".join(reversed(TABLES)) + " RESTART IDENTITY CASCADE")
    pg.commit()
    counts = {}
    for t in TABLES:
        counts[t] = _copy_table(src, pg, t)
    pg.execute("SELECT setval(pg_get_serial_sequence('calls','id'), COALESCE((SELECT max(id) FROM calls), 0) + 1, false)")
    pg.commit()
    print(f"copied in {time.time() - t0:.0f}s")

    # ── verify ────────────────────────────────────────────────────────────────────────────────────────────────
    bad = 0
    def close(x, y):
        if x is None or y is None:
            return x == y
        return abs(x - y) <= 1e-9 * max(1.0, abs(x), abs(y))

    print(f"\n{'table':14} {'sqlite':>10} {'postgres':>10}  checksum")
    for t in TABLES:
        a, b = _checksum(src, t), _checksum(pg, t)
        ok = len(a) == len(b) and all(close(x, y) for x, y in zip(a, b, strict=True))
        bad += not ok
        print(f"{t:14} {int(a[0]):>10,} {int(b[0]):>10,}  {'ok' if ok else 'MISMATCH ' + str((a, b))}")
    model = os.environ.get("FINCLATOR_ACTIVE_MODEL")
    ma = matrix.build(src, write=False, model=model)
    mb = matrix.build(pg, write=False, model=model)
    for m in (ma, mb):
        m.pop("generated_at", None)
    same = json.dumps(ma, sort_keys=True) == json.dumps(mb, sort_keys=True)
    bad += not same
    print("matrix identical:", same)
    if not same:
        for k in ma["cells"]:
            if ma["cells"][k] != mb["cells"].get(k):
                print("  ", k, ma["cells"][k], "≠", mb["cells"].get(k))
    print("\nRESULT:", "OK" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
