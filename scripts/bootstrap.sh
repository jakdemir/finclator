#!/bin/bash
# Create venv, install, backfill the three CSVs, print prefilter stats.
set -e
cd "$(dirname "$0")/.."
rm -rf .venv
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[dev]"
rm -f data/finclator.db data/finclator.db-wal data/finclator.db-shm
touch src/__init__.py
.venv/bin/python -m src.fetch csv data/TwExportly_santmanukyan_tweets_2025_11_30_1000.csv SantManukyan
.venv/bin/python -m src.fetch csv data/TwExportly_laplace2011_tweets_2025_11_30_1000.csv laplace2011
.venv/bin/python -m src.fetch csv data/TwExportly_APompliano_tweets_2025_11_30.csv APompliano
sqlite3 data/finclator.db "SELECT handle, count(*) total, sum(relevant) relevant, sum(is_reply) replies, min(created_at) first, max(created_at) last FROM tweets GROUP BY handle;"
sqlite3 data/finclator.db "SELECT assets_hint, count(*) FROM tweets WHERE relevant=1 GROUP BY 1 ORDER BY 2 DESC;"
