"""Run the 4 classifier tuning variants on the holdout gold set and print a comparison table.
Usage: PYTHONPATH=. .venv/bin/python scripts/tune_variants.py [gold.jsonl] [N]
Requires Ollama with OLLAMA_NUM_PARALLEL=8 (scripts/ollama_serve.sh)."""
import json
import os
import subprocess
import sys

gold = sys.argv[1] if len(sys.argv) > 1 else "data/labels_holdout.jsonl"
n = sys.argv[2] if len(sys.argv) > 2 else "100000"
BASE = {"FINCLATOR_MODEL_BASE_URL": "http://localhost:11434/v1", "FINCLATOR_NUM_CTX": "6144", "PYTHONPATH": "."}
VARIANTS = {
    # name: (description, env overrides)
    "A_terse_par8":   ("terse output, no thinking, 8 parallel streams (current production)",
                       {"FINCLATOR_TERSE": "1", "FINCLATOR_THINK": "0", "FINCLATOR_WORKERS": "8", "FINCLATOR_BATCH_SIZE": "1"}),
    "B_full_par8":    ("full JSON output (is_call field, whitespace), no thinking, 8 streams",
                       {"FINCLATOR_TERSE": "0", "FINCLATOR_THINK": "0", "FINCLATOR_WORKERS": "8", "FINCLATOR_BATCH_SIZE": "1"}),
    "C_batch4_par8":  ("terse, 4 tweets per request, 8 streams",
                       {"FINCLATOR_TERSE": "1", "FINCLATOR_THINK": "0", "FINCLATOR_WORKERS": "8", "FINCLATOR_BATCH_SIZE": "4"}),
    "D_think_par8":   ("terse, thinking ON (reasoning tokens before the answer), 8 streams",
                       {"FINCLATOR_TERSE": "1", "FINCLATOR_THINK": "1", "FINCLATOR_WORKERS": "8", "FINCLATOR_BATCH_SIZE": "1"}),
}
results = []
for name, (desc, env) in VARIANTS.items():
    print(f"\n=== {name}: {desc}", flush=True)
    p = subprocess.run([".venv/bin/python", "scripts/score_variant.py", name, gold, n],
                       env={**os.environ, **BASE, **env}, capture_output=True, text=True)
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if not line:
        print("FAILED\n", p.stdout[-800:], p.stderr[-1500:])
        continue
    r = json.loads(line[7:])
    r["desc"] = desc
    results.append(r)
    print({k: r[k] for k in ("n", "seconds", "tweets_per_min", "is_call_acc", "call_precision", "call_recall", "dir_acc", "hor_acc", "errors")})

hdr = f"{'variant':16}{'tw/min':>8}{'s/tweet':>9}{'is_call':>9}{'prec':>7}{'rec':>7}{'F1':>7}{'dir':>7}{'hor':>7}{'err':>5}"
lines = [hdr]
for r in results:
    f = lambda v: "  –  " if v is None else f"{v:.2f}"  # noqa: E731
    lines.append(f"{r['variant']:16}{r['tweets_per_min']:>8.0f}{r['s_per_tweet']:>9.3f}{r['is_call_acc']:>9.3f}"
                 f"{r['call_precision']:>7.2f}{r['call_recall']:>7.2f}{r['call_f1']:>7.2f}{f(r['dir_acc']):>7}{f(r['hor_acc']):>7}{r['errors']:>5}")
table = "\n".join(lines)
print("\n" + table)
with open("data/tune_variants.json", "w") as fh:
    json.dump(results, fh, indent=1)
with open("data/tune_variants.txt", "w") as fh:
    fh.write(f"gold={gold}\n" + "\n".join(f"{k}: {d}" for k, (d, _) in VARIANTS.items()) + "\n\n" + table + "\n")
print("\nwrote data/tune_variants.{json,txt}")
