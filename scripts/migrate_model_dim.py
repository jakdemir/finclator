"""One-off migration: make model a first-class dimension.
- calls: UNIQUE(tweet_id, asset) → UNIQUE(tweet_id, asset, model)
- tweets.classified (flag) → classified_by table (tweet_id, model)
- trust: PRIMARY KEY (handle, asset, horizon) → (model, handle, asset, horizon)
"""
from src.db import connect

conn = connect()
conn.execute("PRAGMA foreign_keys=OFF")
cols = {r["name"] for r in conn.execute("PRAGMA table_info(trust)")}
if "model" in cols:
    print("already migrated")
    raise SystemExit

conn.executescript("""
BEGIN;
CREATE TABLE calls_new (
    id INTEGER PRIMARY KEY, tweet_id TEXT NOT NULL REFERENCES tweets(id), handle TEXT NOT NULL,
    asset TEXT NOT NULL, direction TEXT NOT NULL, horizon TEXT NOT NULL, confidence REAL NOT NULL,
    price_target REAL, quote TEXT, called_at TEXT NOT NULL, model TEXT NOT NULL,
    UNIQUE(tweet_id, asset, model));
INSERT INTO calls_new SELECT id, tweet_id, handle, asset, direction, horizon, confidence, price_target, quote, called_at, model FROM calls;
DROP TABLE calls; ALTER TABLE calls_new RENAME TO calls;
CREATE INDEX IF NOT EXISTS ix_calls_cell ON calls(model, asset, horizon, called_at);

CREATE TABLE IF NOT EXISTS classified_by (tweet_id TEXT NOT NULL REFERENCES tweets(id), model TEXT NOT NULL, at TEXT,
    PRIMARY KEY (tweet_id, model));
INSERT OR IGNORE INTO classified_by SELECT id, 'claude-fable-5.1/interactive', NULL FROM tweets WHERE classified=1;

CREATE TABLE trust_new (model TEXT NOT NULL, handle TEXT NOT NULL, asset TEXT NOT NULL, horizon TEXT NOT NULL,
    n INTEGER NOT NULL, correct REAL NOT NULL, score REAL NOT NULL, computed_at TEXT NOT NULL,
    PRIMARY KEY (model, handle, asset, horizon));
DROP TABLE trust; ALTER TABLE trust_new RENAME TO trust;
COMMIT;
""")
print("migrated:", conn.execute("SELECT count(*) FROM classified_by").fetchone()[0], "classified_by rows")
