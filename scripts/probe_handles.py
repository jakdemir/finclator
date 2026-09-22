"""Probe roster accounts that have zero stored tweets: does the handle still exist / is it protected?

    PYTHONPATH=. .venv/bin/python scripts/probe_handles.py [--deactivate]
"""
import sys

from src.db import connect, log
from src.fetch import _client, _get

conn = connect()
handles = [r[0] for r in conn.execute("SELECT handle FROM accounts WHERE active=1 AND handle NOT IN (SELECT DISTINCT handle FROM tweets)")]
print("never fetched:", handles)
with _client() as c:
    for h in handles:
        try:
            r = _get(c, "/twitter/user/info", userName=h)
        except Exception as e:  # noqa: BLE001
            r = {"error": str(e)}
        d = r.get("data") or {}
        print(h, "→", {k: d.get(k) for k in ("userName", "statusesCount", "protected", "unavailable", "followers")},
              r.get("msg") or r.get("error") or "")
        gone = not d.get("userName") or d.get("unavailable") or d.get("protected")
        if gone and "--deactivate" in sys.argv:
            conn.execute("UPDATE accounts SET active=0 WHERE handle=?", (h,))
            conn.commit()
            log(f"probe_handles: deactivated @{h} (unavailable/protected/not found)")
