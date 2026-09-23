"""Live smoke of the hybrid: classify N pending tweets for the '+jev' dimension, print funnel + timing."""
import os
import sys
import time

os.environ.setdefault("FINCLATOR_MODEL_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("FINCLATOR_WORKERS", "8")
os.environ.setdefault("FINCLATOR_BATCH_SIZE", "4")
from src import classify, models  # noqa: E402
from src.db import connect  # noqa: E402

n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
conn = connect()
m = models.classifier_model()
print("tag:", m, "| text model:", models.text_model(), "| gate:", models.GATE_ON)
print("pending for tag:", len(classify.pending(conn, None, m)))
t0 = time.time()
print("result:", classify.classify_pending(conn, n), f"in {time.time() - t0:.0f}s")
r = conn.execute("""SELECT (SELECT count(*) FROM classified_by WHERE model=?) cls, (SELECT count(*) FROM calls WHERE model=?) calls,
                    (SELECT count(*) FROM calls WHERE model=? AND gate_p IS NOT NULL) with_gate,
                    (SELECT count(*) FROM gate) gate_rows, (SELECT min(model)||'..'||max(model) FROM gate) jev""",
                 (m, m, m)).fetchone()
print(dict(r))
