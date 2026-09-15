"""Daily closes from Yahoo Finance chart API (no key). Fetched in full once, then tail-refreshed.

BTC  → BTC-USD      GOLD → GC=F (COMEX front month)      SPX → ^GSPC
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone

import httpx

from .db import connect

YAHOO = {"BTC": "BTC-USD", "GOLD": "GC=F", "SPX": "^GSPC"}
_UA = {"User-Agent": "Mozilla/5.0"}


def fetch_yahoo(asset: str, start: date) -> list[tuple[str, float]]:
    p1 = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.now(timezone.utc).timestamp()) + 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{YAHOO[asset]}"
    r = httpx.get(url, params={"period1": p1, "period2": p2, "interval": "1d"}, headers=_UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    out = []
    for ts, c in zip(res["timestamp"], closes):
        if c is not None:
            out.append((datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(), float(c)))
    return out


def update_prices(conn: sqlite3.Connection, full_from: date = date(2020, 1, 1)) -> dict[str, int]:
    result = {}
    for asset in YAHOO:
        last = conn.execute("SELECT max(date) FROM prices WHERE asset=?", (asset,)).fetchone()[0]
        start = full_from if not last else date.fromisoformat(last) - timedelta(days=7)
        rows = fetch_yahoo(asset, start)
        conn.executemany("INSERT OR REPLACE INTO prices(asset, date, close) VALUES(?,?,?)",
                         [(asset, d, c) for d, c in rows])
        conn.commit()
        result[asset] = len(rows)
    return result


def close_on_or_after(conn: sqlite3.Connection, asset: str, d: str, max_gap_days: int = 7) -> tuple[str, float] | None:
    """First available close on/after date d (skips weekends/holidays), within max_gap_days."""
    limit = (date.fromisoformat(d[:10]) + timedelta(days=max_gap_days)).isoformat()
    row = conn.execute(
        "SELECT date, close FROM prices WHERE asset=? AND date>=? AND date<=? ORDER BY date LIMIT 1",
        (asset, d[:10], limit),
    ).fetchone()
    return (row["date"], row["close"]) if row else None


if __name__ == "__main__":
    conn = connect()
    print(update_prices(conn))
    for r in conn.execute("SELECT asset, min(date), max(date), count(*) FROM prices GROUP BY asset"):
        print(tuple(r))
