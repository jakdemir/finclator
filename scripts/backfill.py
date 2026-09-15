"""3-year backfill for every roster account, N accounts in parallel. Resumable.
Usage: PYTHONPATH=. .venv/bin/python scripts/backfill.py [--workers 8] [--pages N] [handle ...]
"""
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone
from queue import Queue

from src.db import DB_PATH, connect, log
from src.fetch import fetch_account, sync_roster

UNTIL = (datetime.now(timezone.utc) - timedelta(days=3 * 365)).date().isoformat()

args = sys.argv[1:]
workers, pages = 8, 2000
for flag in ("--workers", "--pages"):
    if flag in args:
        i = args.index(flag)
        val = int(args[i + 1])
        del args[i:i + 2]
        if flag == "--workers":
            workers = val
        else:
            pages = val

conn0 = connect()
sync_roster(conn0)
handles = [h.lower() for h in args] or [r["handle"] for r in conn0.execute("SELECT handle FROM accounts WHERE active=1")]
q: Queue = Queue()
for h in handles:
    oldest = conn0.execute("SELECT min(created_at) FROM tweets WHERE handle=? AND source='twitterapi'", (h,)).fetchone()[0]
    done = conn0.execute("SELECT sampling, rate_per_year FROM accounts WHERE handle=?", (h,)).fetchone()
    if (oldest and oldest[:10] <= UNTIL) or (done and done["sampling"]):
        log(f"{h}: already backfilled, skip")
        continue
    q.put(h)
conn0.close()
log(f"{q.qsize()} accounts to fetch with {workers} workers, back to {UNTIL}")


def worker():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    while True:
        try:
            h = q.get_nowait()
        except Exception:
            return
        try:
            n = fetch_account(conn, h, max_pages=pages, backfill=True, until=UNTIL)
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
log("backfill complete")
