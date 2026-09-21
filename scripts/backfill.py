"""Parallel fetch: every active account (or the handles given) from its watermark to now, N accounts at a time.
Same primitive as the daily run (`fetch.fetch_account`); an account with no stored tweets is pulled back
BACKFILL_YEARS. Resumable: the watermark only advances after an account's whole span succeeded.
Usage: PYTHONPATH=. .venv/bin/python scripts/backfill.py [--workers 8] [handle ...]
"""
import sys
import threading
from queue import Queue

from src.db import connect, log
from src.fetch import LAST_COST, MIN_CREDITS, credits, fetch_account, sync_roster

args = sys.argv[1:]
workers = 8
if "--workers" in args:
    i = args.index("--workers")
    workers = int(args[i + 1])
    del args[i:i + 2]

conn0 = connect()
sync_roster(conn0)
handles = [h.lower() for h in args] or [r["handle"] for r in conn0.execute("SELECT handle FROM accounts WHERE active=1")]
conn0.close()
q: Queue = Queue()
for h in handles:
    q.put(h)
before = credits()
if before < MIN_CREDITS:
    sys.exit(f"balance {before:,} credits < floor {MIN_CREDITS:,}")
log(f"backfill: {q.qsize()} accounts with {workers} workers; balance ${before / 1e5:.2f}")


def worker():
    conn = connect()
    if getattr(conn, "backend", "sqlite") == "sqlite":
        conn.execute("PRAGMA busy_timeout=60000")
    while True:
        try:
            h = q.get_nowait()
        except Exception:
            return
        try:
            n = fetch_account(conn, h)
            tot, rel = conn.execute("SELECT count(*), sum(relevant) FROM tweets WHERE handle=?", (h,)).fetchone()
            log(f"{h}: +{n} → {tot} total, {rel} relevant  [{q.qsize()} left]")
        except Exception as e:  # noqa: BLE001
            log(f"{h}: ERROR {e}")
        finally:
            q.task_done()


threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
for t in threads:
    t.start()
for t in threads:
    t.join()
after = credits()
est = sum(LAST_COST.values())
log(f"backfill complete: ≈{est:,} credits (${est / 1e5:.3f}) by count; balance ${after / 1e5:.2f} (lazy)")
