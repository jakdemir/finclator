"""Throughput benchmark: same tweets, varying client concurrency. No DB writes."""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("FINCLATOR_MODEL_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("FINCLATOR_MODEL", "qwen3.6-local:35b-a3b-q4_K_M")
from src.classify import make_classifier, pending
from src.db import connect

run, m = make_classifier()
rows = pending(connect(), 96, m)
run(rows[0])  # warm-up / model load
for w in [int(x) for x in sys.argv[1:]] or [1, 4, 8, 12]:
    t0 = time.time()
    with ThreadPoolExecutor(w) as p:
        res = list(p.map(run, rows))
    dt = time.time() - t0
    print(f"workers={w:2d}  {len(rows)} tweets in {dt:5.1f}s  →  {len(rows)/dt*60:5.0f}/min  ({dt/len(rows):.2f}s/tweet)  calls={sum(1 for r in res if r.get('is_call'))}", flush=True)
