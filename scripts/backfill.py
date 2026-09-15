"""3-year backfill for every roster account. Resumable: skips accounts whose oldest tweet is already < UNTIL.
Usage: PYTHONPATH=. .venv/bin/python scripts/backfill.py [--pages N] [handle ...]
"""
import sys
from datetime import datetime, timedelta, timezone

from src.db import connect
from src.fetch import fetch_account, sync_roster

UNTIL = (datetime.now(timezone.utc) - timedelta(days=3 * 365)).date().isoformat()

args = sys.argv[1:]
pages = 2000
if "--pages" in args:
    i = args.index("--pages")
    pages = int(args[i + 1])
    del args[i:i + 2]

conn = connect()
sync_roster(conn)
handles = [h.lower() for h in args] or [r["handle"] for r in conn.execute("SELECT handle FROM accounts WHERE active=1")]
for h in handles:
    oldest = conn.execute("SELECT min(created_at) FROM tweets WHERE handle=? AND source='twitterapi'", (h,)).fetchone()[0]
    if oldest and oldest[:10] <= UNTIL:
        print(f"{h}: already backfilled to {oldest[:10]}, skip")
        continue
    print(f"{h}: fetching back to {UNTIL} (max {pages} pages)", flush=True)
    n = fetch_account(conn, h, max_pages=pages, backfill=True, until=UNTIL)
    tot, rel = conn.execute("SELECT count(*), sum(relevant) FROM tweets WHERE handle=?", (h,)).fetchone()
    print(f"{h}: +{n} inserted → {tot} total, {rel} relevant", flush=True)
