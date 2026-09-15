"""Tweet acquisition: roster sync, CSV backfill (TwExportly), and twitterapi.io incremental fetch."""
from __future__ import annotations

import csv
import os
import sqlite3
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
import yaml

from .db import connect
from .prefilter import is_relevant

ROOT = Path(__file__).resolve().parent.parent
ROSTER = ROOT / "roster.yaml"
API = "https://api.twitterapi.io"


# ---------- roster ----------

def sync_roster(conn: sqlite3.Connection) -> list[dict]:
    accounts = yaml.safe_load(ROSTER.read_text())["accounts"]
    for a in accounts:
        conn.execute(
            """INSERT INTO accounts(handle, display_name, school, language, active, updated_at)
               VALUES(?,?,?,?,1,?)
               ON CONFLICT(handle) DO UPDATE SET display_name=excluded.display_name,
                 school=excluded.school, language=excluded.language, active=1""",
            (a["handle"].lower(), a.get("display_name"), a["school"], a.get("language", "en"),
             datetime.now(timezone.utc).isoformat()),
        )
    conn.commit()
    return accounts


# ---------- insert ----------

def _insert(conn: sqlite3.Connection, rows: list[dict]) -> int:
    n = 0
    for r in rows:
        rel, assets = is_relevant(r["text"], r["is_reply"])
        cur = conn.execute(
            """INSERT OR IGNORE INTO tweets(id, handle, created_at, text, is_reply, lang, source, assets_hint, relevant)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (r["id"], r["handle"], r["created_at"], r["text"], int(r["is_reply"]), r.get("lang"),
             r["source"], ",".join(assets), int(rel)),
        )
        n += cur.rowcount
    conn.commit()
    return n


# ---------- CSV backfill ----------

def import_csv(conn: sqlite3.Connection, path: Path, handle: str) -> int:
    handle = handle.lower()
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            tid = r["tweet_id"].strip("'\" ")
            ts = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            rows.append({
                "id": tid, "handle": handle, "created_at": ts.isoformat(), "text": r["text"],
                "is_reply": r.get("type", "") == "Reply", "lang": r.get("language"), "source": "csv",
            })
    return _insert(conn, rows)


# ---------- twitterapi.io ----------

def _client() -> httpx.Client:
    key = os.environ.get("TWITTERAPI_IO_KEY") or _dotenv("TWITTERAPI_IO_KEY")
    if not key:
        raise RuntimeError("TWITTERAPI_IO_KEY not set")
    return httpx.Client(base_url=API, headers={"X-API-Key": key}, timeout=30)


def _dotenv(name: str) -> str | None:
    p = ROOT / ".env"
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    return None


MAX_TWEETS_PER_YEAR = 2000  # originals; heavier posters are noise-dominated and expensive


def _get(c: httpx.Client, path: str, **params) -> dict:
    for attempt in range(5):
        r = c.get(path, params=params)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))  # free tier: 1 req / 5 s
            continue
        if r.status_code == 402:
            raise RuntimeError("twitterapi.io: out of credits — top up at https://twitterapi.io")
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited on {path}")


def _norm(t: dict, handle: str) -> dict:
    ts = parsedate_to_datetime(t["createdAt"]).astimezone(timezone.utc)
    return {
        "id": str(t["id"]), "handle": handle, "created_at": ts.isoformat(), "text": t.get("text", ""),
        "is_reply": bool(t.get("isReply")), "lang": t.get("lang"), "source": "twitterapi",
    }


def _rate_per_year(tweets: list[dict]) -> float:
    """Extrapolate originals/year from a page span."""
    if len(tweets) < 2:
        return 0.0
    a = parsedate_to_datetime(tweets[0]["createdAt"])
    b = parsedate_to_datetime(tweets[-1]["createdAt"])
    days = max(1.0, abs((a - b).total_seconds()) / 86400)
    return len(tweets) / days * 365


def fetch_account(conn: sqlite3.Connection, handle: str, max_pages: int = 50, backfill: bool = False,
                  until: str | None = None) -> int:
    """Fetch original (non-reply) tweets newer than the watermark, or back to `until` if backfill.
    Aborts with 0 if the account posts > MAX_TWEETS_PER_YEAR originals (measured on the first page)."""
    handle = handle.lower()
    row = conn.execute("SELECT last_tweet_id FROM accounts WHERE handle=?", (handle,)).fetchone()
    since = None if backfill else (row["last_tweet_id"] if row else None)
    since_int = int(since) if since else 0

    with _client() as c:
        info = _get(c, "/twitter/user/info", userName=handle).get("data") or {}
        if info.get("followers"):
            conn.execute("UPDATE accounts SET followers=? WHERE handle=?", (info["followers"], handle))

        cursor, pages, batch, newest, inserted, last_date = "", 0, [], since_int, 0, ""
        done = False
        probe: list[dict] = []
        while pages < max_pages and not done:
            time.sleep(1.0)
            resp = _get(c, "/twitter/user/last_tweets", userName=handle, cursor=cursor, includeReplies="false")
            data = resp.get("data") or {}
            tweets = [t for t in (data.get("tweets") or []) if not t.get("isReply")]
            if not tweets:
                break
            if backfill and pages < 3:
                probe.extend(tweets)
                if pages == 2 or not resp.get("has_next_page"):
                    rate = _rate_per_year(probe)
                    if rate > MAX_TWEETS_PER_YEAR:
                        print(f"  {handle}: ~{rate:,.0f} originals/yr > {MAX_TWEETS_PER_YEAR}, deactivating", flush=True)
                        conn.execute("UPDATE accounts SET active=0 WHERE handle=?", (handle,))
                        conn.commit()
                        return 0
            for t in tweets:
                tid = int(t["id"])
                if tid <= since_int:
                    done = True
                    break
                n = _norm(t, handle)
                if until and n["created_at"] < until:
                    done = True
                    break
                newest = max(newest, tid)
                batch.append(n)
                last_date = n["created_at"][:10]
            pages += 1
            if len(batch) >= 500:
                inserted += _insert(conn, batch)  # checkpoint long backfills
                batch = []
                print(f"  {handle}: {pages} pages, {inserted} inserted, at {last_date}", flush=True)
            if not resp.get("has_next_page") or not resp.get("next_cursor"):
                break
            cursor = resp["next_cursor"]

    n = inserted + _insert(conn, batch)
    if newest > since_int:
        conn.execute("UPDATE accounts SET last_tweet_id=?, updated_at=? WHERE handle=?",
                     (str(newest), datetime.now(timezone.utc).isoformat(), handle))
        conn.commit()
    return n


def fetch_all(conn: sqlite3.Connection, max_pages: int = 20) -> dict[str, int]:
    out = {}
    for a in conn.execute("SELECT handle FROM accounts WHERE active=1"):
        out[a["handle"]] = fetch_account(conn, a["handle"], max_pages=max_pages)
    return out


if __name__ == "__main__":
    import sys
    conn = connect()
    sync_roster(conn)
    if len(sys.argv) > 2 and sys.argv[1] == "csv":
        # python -m src.fetch csv data/file.csv handle
        print(import_csv(conn, Path(sys.argv[2]), sys.argv[3]), "inserted")
    elif len(sys.argv) > 1:
        print(fetch_account(conn, sys.argv[1], backfill="--backfill" in sys.argv), "inserted")
    else:
        print(fetch_all(conn))
