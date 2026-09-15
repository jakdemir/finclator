"""3x3 matrix: for each (asset, horizon) aggregate recent calls, weighted by trust × confidence × recency.

Recency: exponential decay with half-life = 1/3 of the horizon's maturity window, and a hard cutoff at the
full window (a SHORT call older than 3 months is stale by definition).
School aggregation: sum of member weights (a one-person school cannot dominate). Written to data/matrix.json.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .db import connect
from .evaluate import MATURITY_DAYS
from .score import trust_for

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "matrix.json"
ASSETS = ("BTC", "GOLD", "SPX")
HORIZONS = ("SHORT", "MEDIUM", "LONG")
NEUTRAL_BAND = 0.15   # |net| below this → NEUTRAL
MIN_WEIGHT = 0.3      # below this total weight → N/A (insufficient data)


def _label(net: float, total: float) -> str:
    if total < MIN_WEIGHT:
        return "N/A"
    if net > NEUTRAL_BAND:
        return "BUY"
    if net < -NEUTRAL_BAND:
        return "SELL"
    return "NEUTRAL"


def build(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    schools = {r["handle"]: r["school"] for r in conn.execute("SELECT handle, school FROM accounts")}
    matrix: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "cells": {}}

    for asset in ASSETS:
        for horizon in HORIZONS:
            window = MATURITY_DAYS[horizon]
            half_life = window / 3
            since = (today - timedelta(days=window)).isoformat()
            rows = conn.execute("""SELECT handle, direction, confidence, called_at, quote, tweet_id FROM calls
                                   WHERE asset=? AND horizon=? AND called_at>=? ORDER BY called_at DESC""",
                                (asset, horizon, since)).fetchall()
            # latest call per account dominates; older ones from the same account decay
            per_school: dict[str, dict] = {}
            contributors = []
            buy = sell = neutral = 0.0
            for r in rows:
                age = (today - date.fromisoformat(r["called_at"][:10])).days
                w = trust_for(conn, r["handle"], asset, horizon) * r["confidence"] * math.exp(-math.log(2) * age / half_life)
                d = r["direction"]
                if d == "BUY":
                    buy += w
                elif d == "SELL":
                    sell += w
                else:
                    neutral += w
                s = per_school.setdefault(schools.get(r["handle"], "?"), {"buy": 0.0, "sell": 0.0, "neutral": 0.0})
                s["buy" if d == "BUY" else "sell" if d == "SELL" else "neutral"] += w
                contributors.append({"handle": r["handle"], "direction": d, "date": r["called_at"][:10],
                                     "weight": round(w, 3), "quote": r["quote"], "tweet_id": r["tweet_id"]})
            total = buy + sell + neutral
            net = (buy - sell) / total if total else 0.0
            matrix["cells"][f"{asset}:{horizon}"] = {
                "asset": asset, "horizon": horizon, "label": _label(net, total),
                "net": round(net, 3), "buy": round(buy, 3), "sell": round(sell, 3), "neutral": round(neutral, 3),
                "n_calls": len(rows),
                "schools": {k: {**{kk: round(vv, 3) for kk, vv in v.items()},
                                "label": _label((v["buy"] - v["sell"]) / (sum(v.values()) or 1), sum(v.values()))}
                            for k, v in per_school.items()},
                "contributors": contributors[:15],
            }
    OUT.write_text(json.dumps(matrix, indent=1, ensure_ascii=False))
    return matrix


def print_grid(m: dict) -> None:
    print(f"{'':6}" + "".join(f"{h:>10}" for h in HORIZONS))
    for a in ASSETS:
        print(f"{a:6}" + "".join(f"{m['cells'][f'{a}:{h}']['label']:>10}" for h in HORIZONS))


if __name__ == "__main__":
    print_grid(build(connect()))
