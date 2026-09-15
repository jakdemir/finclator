#!/bin/bash
set -e
cd "$(dirname "$0")/.."
cat data/labels_part_0*.jsonl > data/labels_backfill.jsonl
wc -l data/labels_backfill.jsonl
.venv/bin/python -m src.classify import data/labels_backfill.jsonl claude-fable-5.1/interactive
sqlite3 data/finclator.db "SELECT handle, asset, horizon, direction, count(*) FROM calls GROUP BY 1,2,3,4 ORDER BY 1,2,3,4;"
echo "== evaluate"; .venv/bin/python -m src.evaluate
echo "== score"; .venv/bin/python -m src.score
echo "== matrix"; .venv/bin/python -m src.matrix
rm -f data/pending_part_* data/labels_part_* data/pending.jsonl
