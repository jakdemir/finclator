"""Evaluate matured calls against price history.

Horizon maturity (spec): SHORT 3 months, MEDIUM 12 months, LONG 24 months (evaluation point inside the 1-5y band).
Direction threshold ("flat" band) is volatility-scaled: K_SIGMA * sigma_daily * sqrt(days) at entry, per asset.
Price targets: hit if any close within the horizon reaches the target (>= for BUY, <= for SELL).
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, datetime, timedelta, timezone

from .db import connect
from .prices import close_on_or_after

MATURITY_DAYS = {"SHORT": 90, "MEDIUM": 365, "LONG": 730}
K_SIGMA = 0.5  # half a standard deviation of the horizon move counts as "flat"


def _daily_sigma(conn: sqlite3.Connection, asset: str, entry: str, lookback_days: int = 365) -> float:
    start = (date.fromisoformat(entry) - timedelta(days=lookback_days)).isoformat()
    closes = [r["close"] for r in conn.execute(
        "SELECT close FROM prices WHERE asset=? AND date>=? AND date<=? ORDER BY date", (asset, start, entry))]
    if len(closes) < 30:
        return {"BTC": 0.035, "GOLD": 0.01, "SPX": 0.011}[asset]
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    mu = sum(rets) / len(rets)
    return math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1))


def _trading_days(asset: str, days: int) -> int:
    return days if asset == "BTC" else round(days * 252 / 365)


def _extreme(conn: sqlite3.Connection, asset: str, start: str, end: str, direction: str) -> float | None:
    fn = "max" if direction == "BUY" else "min"
    return conn.execute(f"SELECT {fn}(close) FROM prices WHERE asset=? AND date>? AND date<=?",
                        (asset, start, end)).fetchone()[0]


def evaluate(conn: sqlite3.Connection, today: date | None = None) -> int:
    today = today or datetime.now(timezone.utc).date()
    rows = conn.execute("""
        SELECT c.id, c.asset, c.direction, c.horizon, c.called_at, c.price_target
        FROM calls c LEFT JOIN outcomes o ON o.call_id = c.id
        WHERE o.call_id IS NULL""").fetchall()
    n = 0
    for c in rows:
        entry_d = c["called_at"][:10]
        exit_d = (date.fromisoformat(entry_d) + timedelta(days=MATURITY_DAYS[c["horizon"]])).isoformat()
        if date.fromisoformat(exit_d) > today:
            continue
        entry = close_on_or_after(conn, c["asset"], entry_d)
        exit_ = close_on_or_after(conn, c["asset"], exit_d)
        if not entry or not exit_:
            continue
        ret = (exit_[1] - entry[1]) / entry[1] * 100
        sigma = _daily_sigma(conn, c["asset"], entry[0])
        thr = K_SIGMA * sigma * math.sqrt(_trading_days(c["asset"], MATURITY_DAYS[c["horizon"]])) * 100
        actual = "NEUTRAL" if abs(ret) < thr else ("BUY" if ret > 0 else "SELL")
        pred = c["direction"]
        if pred == actual:
            result = "CORRECT"
        elif "NEUTRAL" in (pred, actual):
            result = "PARTIAL"   # off by one step
        else:
            result = "WRONG"     # opposite direction

        target_hit, extreme = None, None
        if c["price_target"] and pred in ("BUY", "SELL"):
            extreme = _extreme(conn, c["asset"], entry[0], exit_[0], pred)
            if extreme is not None:
                target_hit = int(extreme >= c["price_target"]) if pred == "BUY" else int(extreme <= c["price_target"])

        conn.execute("""INSERT INTO outcomes(call_id, entry_date, exit_date, entry_close, exit_close, return_pct,
                        threshold_pct, actual, result, target_hit, extreme, evaluated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (c["id"], entry[0], exit_[0], entry[1], exit_[1], ret, thr, actual, result, target_hit, extreme,
                      datetime.now(timezone.utc).isoformat()))
        n += 1
    conn.commit()
    return n


if __name__ == "__main__":
    conn = connect()
    print(evaluate(conn), "outcomes written")
    for r in conn.execute("""SELECT c.handle, c.asset, c.horizon, o.result, count(*) FROM outcomes o JOIN calls c ON c.id=o.call_id
                             GROUP BY 1,2,3,4 ORDER BY 1,2,3,4"""):
        print(tuple(r))
