"""Probe a curated subset of data/candidates.csv (2 timeline pages each) and write data/candidates_probed.csv.
Curation: all seeds + followings that are finance-relevant (bio_score>=1 or in EXTRA)."""
import csv
import sys
import time

from scripts.candidates import probe
from src.fetch import _client

# followings that look like finfluencers but have keyword-poor bios
EXTRA = {
    "profdemirtas", "mahfiegilmez", "michaeljburry", "raydalio", "billackman", "fundstrat", "lukegromen",
    "tuncsatiroglu", "atillayesilada1", "aswathdamodaran", "isyatirim", "gavinsbaker", "citrini", "kivancozbilgic",
    "jam_croissant", "refetgurkaynak", "chickengenius", "hamptonism", "perihantantug", "techcharts", "brad_setser",
    "zerohedge_", "burak_tamac", "bitcoinfear", "mmcrypto", "tedpillows", "nsquaredvalue", "arkham", "litcapital",
    "milesdeutscher", "amitisinvesting", "burrytracker", "zerohedge", "nntaleb", "yanisvaroufakis", "gokhangark",
    "zulalmtn", "wolfcapitalist", "barchart", "peterschiff", "peterlbrandt", "100trillionusd", "santmanukyan",
    "matt_levine", "sinaafra",
}

rows = list(csv.DictReader(open("data/candidates.csv")))
todo = [r for r in rows if r["source"] != "following" or int(r.get("bio_score") or 0) >= 1
        or r["handle"].lower() in EXTRA]
print(f"probing {len(todo)} of {len(rows)}", flush=True)

out = []
with _client() as c:
    for i, r in enumerate(todo, 1):
        try:
            r.update(probe(c, r["handle"]))
        except Exception as e:  # noqa: BLE001
            print(f"  {r['handle']}: {e}", file=sys.stderr, flush=True)
        out.append(r)
        if i % 10 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
        time.sleep(0.2)

cols = ["handle", "source", "school", "lang", "name", "followers", "statuses", "originals_per_y", "asset_hit_rate",
        "probe_n", "last_tweet", "bio_score", "bio"]
out.sort(key=lambda r: (-(float(r.get("asset_hit_rate") or 0)), -int(r.get("followers") or 0)))
with open("data/candidates_probed.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(out)
print("wrote data/candidates_probed.csv")
