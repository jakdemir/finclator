"""One-shot: classify the whole pending backlog for the hybrid tag, then rebuild everything once."""
import os
import time

os.environ.setdefault("FINCLATOR_MODEL_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("FINCLATOR_WORKERS", "8")
os.environ.setdefault("FINCLATOR_BATCH_SIZE", "4")
from src import audit, classify, evaluate, matrix, models, score, site  # noqa: E402
from src.db import connect, log  # noqa: E402

conn = connect()
m = models.classifier_model()
t0 = time.time()
log(f"hybrid_run: tag={m} pending={len(classify.pending(conn, None, m)):,}")
while True:
    n, calls = classify.classify_pending(conn, 5000)
    log(f"hybrid_run: batch {n} tweets / {calls} calls · {(time.time() - t0) / 60:.1f} min")
    if n == 0:
        break
log(f"hybrid_run: evaluated {evaluate.evaluate(conn)} · trust {score.recompute(conn)}")
matrix.print_grid(matrix.build(conn))
log(f"hybrid_run: audit {audit.build()}")
site.build(conn)
log(f"hybrid_run: done in {(time.time() - t0) / 60:.1f} min")
