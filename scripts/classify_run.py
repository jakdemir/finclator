"""Long-running, resumable classification of the pending backlog with the local model.

Usage (from repo root; model/endpoint default to src.models.DEFAULT_MODEL on local Ollama):
  FINCLATOR_WORKERS=8 PYTHONPATH=. nohup .venv/bin/python scripts/classify_run.py > /dev/null 2>&1 &

Persistence: every labeled tweet is written to `classified_by` (+ `calls`) and committed every 50 tweets inside
classify_pending, so a crash/kill loses ≤50 tweets (~30 s of work). Re-running skips everything already in
`classified_by` for this model — nothing is ever re-classified. Order is newest → oldest.

After every batch: evaluate matured calls → recompute trust → rebuild matrix.json → regenerate audit.html, so the
admin page reflects progress while the run is going. Stop with `pkill -f classify_run.py`.
"""
import os
import sys
import time

from src import audit, classify, evaluate, matrix, score
from src.db import connect, log

BATCH = int(os.environ.get("FINCLATOR_BATCH", "1000"))
if not classify.BASE_URL:
    sys.exit("set FINCLATOR_MODEL_BASE_URL (local model) before running the backlog")

conn = connect()
model = classify.MODEL
total = len(classify.pending(conn, None, model))
log(f"classify_run: model={model} workers={classify.WORKERS} num_ctx={classify.NUM_CTX} pending={total:,}")
done = 0
t0 = time.time()
while True:
    n, calls = classify.classify_pending(conn, BATCH)
    if n == 0:
        break
    done += n
    rate = done / (time.time() - t0) * 60
    left = total - done
    log(f"classify_run: batch done {n} tweets / {calls} calls · {done:,}/{total:,} · {rate:.0f}/min · ETA {left / rate / 60:.1f} h")
    try:
        ev = evaluate.evaluate(conn)
        tr = score.recompute(conn)
        matrix.build(conn)
        audit.build()
        log(f"classify_run: evaluated {ev} new outcomes · {tr} trust rows · matrix + audit rebuilt")
    except Exception as e:  # noqa: BLE001 — a rebuild hiccup must not stop labeling
        log(f"classify_run: post-batch rebuild failed: {type(e).__name__}: {e}")
log(f"classify_run: finished · {done:,} tweets in {(time.time() - t0) / 3600:.2f} h")
