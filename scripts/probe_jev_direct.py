"""Throughput probe: direct TypeSafe API at several worker counts. Writes data/jev_direct_probe.txt."""
import os
import subprocess
import sys

ROOT = "/Users/jakdemir/projects/finclator"
env = dict(os.environ)
for ln in open(os.path.join(ROOT, ".env")):
    ln = ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k, v = ln.split("=", 1)
        env.setdefault(k, v.strip().strip('"'))
env["PYTHONPATH"] = "."
env["JEV_ROUTE"] = "direct"
workers = sys.argv[1:] or ["2", "4", "8"]
out = open(os.path.join(ROOT, "data/jev_direct_probe.txt"), "a")
for w in workers:
    env["JEV_WORKERS"] = w
    r = subprocess.run([".venv/bin/python", "scripts/score_jev.py", "data/labels_holdout.jsonl", "100"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    txt = r.stdout + r.stderr
    out.write(f"\n=== workers={w} rc={r.returncode}\n{txt}\n")
    out.flush()
    print(f"=== workers={w} rc={r.returncode}")
    print(txt[-1500:])
