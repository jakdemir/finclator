"""Tweet → explicit directional calls.

Two modes:
  * API: `classify_pending(conn)` uses ANTHROPIC_API_KEY (weekly cron).
  * Interactive: `export_pending()` writes a JSONL for an assistant session to label;
    `import_labels(path)` loads the result. Same schema either way.

Horizons follow the spec: SHORT 0-3 months, MEDIUM 3-12 months, LONG 1-5 years.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from .db import connect

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("FINCLATOR_MODEL", "claude-sonnet-4-5")

SYSTEM = """You extract explicit, falsifiable market calls from finance-influencer tweets.

Assets: BTC (Bitcoin), GOLD (gold, altın, XAU), SPX (S&P 500 / US equities / Nasdaq as proxy).
Tweets may be Turkish or English.

A CALL is a statement that the price of an asset will go up (BUY), down (SELL), or stay range-bound / the
author is explicitly neutral or waiting (NEUTRAL). Reporting a past move, a news item, a chart with no
opinion, sarcasm you cannot resolve, or general macro talk without a directional claim on the asset is NOT a call.
Be strict: when in doubt, is_call=false.

Horizon (per the author's stated or clearly implied timeframe):
  SHORT  = 0-3 months (days, weeks, "this month", intraday, swing)
  MEDIUM = 3-12 months (this year, next quarters, "coming months")
  LONG   = 1-5 years (cycle, multi-year, structural, "decade", "generational")
If no timeframe is given, infer from context (technical/level talk → SHORT; macro/structural thesis → LONG;
otherwise MEDIUM).

price_target: a numeric level the author expects the asset to reach, in USD (BTC per coin, gold per troy oz,
SPX index points). Convert "100k" → 100000, "$4,500" → 4500. null if no explicit level. A target implies the
direction (target above current price → BUY, below → SELL) unless the author says otherwise.

Respond with JSON only:
{"is_call": bool, "calls": [{"asset": "BTC|GOLD|SPX", "direction": "BUY|SELL|NEUTRAL",
 "horizon": "SHORT|MEDIUM|LONG", "confidence": 0.0-1.0, "price_target": number|null,
 "quote": "<exact span from the tweet in its original language that justifies the label>"}]}
Only include assets the tweet actually takes a stance on. calls=[] when is_call=false."""


def pending(conn: sqlite3.Connection, limit: int | None = None) -> list[sqlite3.Row]:
    q = "SELECT id, handle, created_at, text, assets_hint FROM tweets WHERE relevant=1 AND classified=0 ORDER BY created_at"
    if limit:
        q += f" LIMIT {int(limit)}"
    return conn.execute(q).fetchall()


def store_result(conn: sqlite3.Connection, tweet: sqlite3.Row | dict, result: dict, model: str) -> int:
    n = 0
    tid, handle, created = tweet["id"], tweet["handle"], tweet["created_at"]
    if result.get("is_call"):
        for c in result.get("calls", []):
            if c.get("asset") not in ("BTC", "GOLD", "SPX"):
                continue
            pt = c.get("price_target")
            try:
                pt = float(pt) if pt not in (None, "", "null") else None
            except (TypeError, ValueError):
                pt = None
            conn.execute(
                """INSERT OR REPLACE INTO calls(tweet_id, handle, asset, direction, horizon, confidence, price_target,
                   quote, called_at, model) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (tid, handle, c["asset"], c["direction"], c["horizon"], float(c.get("confidence", 0.5)), pt,
                 c.get("quote"), created, model),
            )
            n += 1
    conn.execute("UPDATE tweets SET classified=1 WHERE id=?", (tid,))
    return n


# ---------- API mode ----------

def classify_pending(conn: sqlite3.Connection, limit: int | None = None) -> tuple[int, int]:
    from anthropic import Anthropic

    client = Anthropic()
    rows = pending(conn, limit)
    tweets_done = calls_made = 0
    for t in rows:
        msg = client.messages.create(
            model=MODEL, max_tokens=600, system=SYSTEM, temperature=0,
            messages=[{"role": "user", "content": f"@{t['handle']} ({t['created_at'][:10]}), assets mentioned: {t['assets_hint']}\n\n{t['text']}"}],
        )
        raw = "".join(getattr(b, "text", "") for b in msg.content).strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"is_call": False, "calls": []}
        calls_made += store_result(conn, t, result, MODEL)
        tweets_done += 1
        if tweets_done % 20 == 0:
            conn.commit()
    conn.commit()
    return tweets_done, calls_made


# ---------- interactive mode ----------

def export_pending(conn: sqlite3.Connection, path: Path, limit: int | None = None) -> int:
    rows = pending(conn, limit)
    with open(path, "w") as f:
        for t in rows:
            f.write(json.dumps({"id": t["id"], "handle": t["handle"], "created_at": t["created_at"],
                                "assets_hint": t["assets_hint"], "text": t["text"]}, ensure_ascii=False) + "\n")
    return len(rows)


def import_labels(conn: sqlite3.Connection, path: Path, model: str) -> tuple[int, int]:
    """JSONL lines: {"id": ..., "is_call": ..., "calls": [...]}"""
    tweets_done = calls_made = 0
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        t = conn.execute("SELECT id, handle, created_at FROM tweets WHERE id=?", (r["id"],)).fetchone()
        if not t:
            continue
        calls_made += store_result(conn, t, r, model)
        tweets_done += 1
    conn.commit()
    return tweets_done, calls_made


if __name__ == "__main__":
    import sys
    conn = connect()
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        print(export_pending(conn, Path(sys.argv[2])), "exported")
    elif len(sys.argv) > 1 and sys.argv[1] == "import":
        print(import_labels(conn, Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "manual"))
    else:
        print(classify_pending(conn))
