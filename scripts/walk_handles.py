"""Timeline-walk backfill for accounts the search index under-serves (0 or very few stored tweets).

    PYTHONPATH=. .venv/bin/python scripts/walk_handles.py durdn mrcollaborative
"""
import sys

from src.db import connect
from src.fetch import credits, walk_timeline

conn = connect()
before = credits()
for h in sys.argv[1:]:
    print(h, walk_timeline(conn, h))
    n = conn.execute("SELECT count(*), coalesce(sum(relevant),0), min(created_at), max(created_at) FROM tweets WHERE handle=?", (h.lower(),)).fetchone()
    print("  stored:", tuple(n))
print("credits before/after (lazy counter):", before, credits())
