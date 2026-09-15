"""SQLite storage. Single file, single writer, zero ops."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finclator.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    handle        TEXT PRIMARY KEY,           -- lowercase, no @
    display_name  TEXT,
    school        TEXT NOT NULL,
    language      TEXT NOT NULL DEFAULT 'en',
    active        INTEGER NOT NULL DEFAULT 1,
    last_tweet_id TEXT,                       -- watermark for incremental fetch
    followers     INTEGER,
    rate_per_year INTEGER,                    -- measured originals/yr at backfill
    sampling      TEXT,                       -- NULL = full timeline; e.g. 'days1-3/month'
    tier          TEXT NOT NULL DEFAULT 'B',
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS tweets (
    id          TEXT PRIMARY KEY,             -- tweet id (string, exact)
    handle      TEXT NOT NULL REFERENCES accounts(handle),
    created_at  TEXT NOT NULL,                -- ISO-8601 UTC
    text        TEXT NOT NULL,
    is_reply    INTEGER NOT NULL DEFAULT 0,
    lang        TEXT,
    source      TEXT NOT NULL,                -- 'csv' | 'twitterapi'
    assets_hint TEXT NOT NULL DEFAULT '',     -- prefilter: 'BTC,GOLD'
    relevant    INTEGER NOT NULL DEFAULT 0,   -- prefilter passed → eligible for LLM
    classified  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_tweets_handle_created ON tweets(handle, created_at);
CREATE INDEX IF NOT EXISTS ix_tweets_pending ON tweets(relevant, classified);

-- One row per (tweet, asset) explicit directional call. Non-calls are not stored here.
CREATE TABLE IF NOT EXISTS calls (
    id          INTEGER PRIMARY KEY,
    tweet_id    TEXT NOT NULL REFERENCES tweets(id),
    handle      TEXT NOT NULL,
    asset       TEXT NOT NULL,                -- BTC | GOLD | SPX
    direction   TEXT NOT NULL,                -- BUY | NEUTRAL | SELL
    horizon     TEXT NOT NULL,                -- SHORT | MEDIUM | LONG
    confidence  REAL NOT NULL,
    price_target REAL,                        -- explicit level if stated (same units as prices table)
    quote       TEXT,                         -- exact span justifying the label (audit trail)
    called_at   TEXT NOT NULL,                -- = tweet created_at
    model       TEXT NOT NULL,
    UNIQUE(tweet_id, asset)
);
CREATE INDEX IF NOT EXISTS ix_calls_cell ON calls(asset, horizon, called_at);

CREATE TABLE IF NOT EXISTS prices (
    asset  TEXT NOT NULL,
    date   TEXT NOT NULL,                     -- YYYY-MM-DD
    close  REAL NOT NULL,
    PRIMARY KEY (asset, date)
);

-- Filled by evaluate.py once a call's horizon has matured.
CREATE TABLE IF NOT EXISTS outcomes (
    call_id      INTEGER PRIMARY KEY REFERENCES calls(id),
    entry_date   TEXT NOT NULL,
    exit_date    TEXT NOT NULL,
    entry_close  REAL NOT NULL,
    exit_close   REAL NOT NULL,
    return_pct   REAL NOT NULL,
    threshold_pct REAL NOT NULL,              -- vol-scaled band used for NEUTRAL
    actual       TEXT NOT NULL,               -- BUY | NEUTRAL | SELL (what the market did)
    result       TEXT NOT NULL,               -- CORRECT | WRONG | PARTIAL  (direction)
    target_hit   INTEGER,                     -- 1 if price_target was touched within the horizon, 0 if not, NULL n/a
    extreme      REAL,                        -- max close (BUY) / min close (SELL) within horizon
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trust (
    handle      TEXT NOT NULL,
    asset       TEXT NOT NULL,                -- or '*' for overall
    horizon     TEXT NOT NULL,                -- or '*' for overall
    n           INTEGER NOT NULL,
    correct     REAL NOT NULL,                -- CORRECT=1, PARTIAL=0.5
    score       REAL NOT NULL,                -- shrunk toward 0.5
    computed_at TEXT NOT NULL,
    PRIMARY KEY (handle, asset, horizon)
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    # additive migrations for existing DBs
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(accounts)")}
    for col, typ in (("rate_per_year", "INTEGER"), ("sampling", "TEXT"), ("tier", "TEXT NOT NULL DEFAULT 'B'")):
        if col not in cols:
            conn.execute(f"ALTER TABLE accounts ADD COLUMN {col} {typ}")
    for table, col, typ in (("calls", "price_target", "REAL"), ("outcomes", "target_hit", "INTEGER"),
                            ("outcomes", "extreme", "REAL")):
        if col not in {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    conn.commit()
    return conn
