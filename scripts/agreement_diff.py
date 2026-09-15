"""Print every gold/pred disagreement from data/agreement_preds.jsonl, grouped by kind."""
import json
import sys

kind = sys.argv[1] if len(sys.argv) > 1 else "all"
rows = [json.loads(l) for l in open("data/agreement_preds.jsonl")]
for r in rows:
    g, p = r["gold"], r["pred"]
    gc = {c["asset"]: c for c in g.get("calls", [])}
    pc = {c.get("asset"): c for c in p.get("calls", []) if c.get("asset") in ("BTC", "GOLD", "SPX")}
    text = r["text"][:400].replace("\n", " ")
    if bool(g["is_call"]) != bool(p.get("is_call")) and kind in ("all", "is_call"):
        who = "EXTRA" if p.get("is_call") else "MISSED"
        src = pc if p.get("is_call") else gc
        lab = "; ".join(f"{a}:{c.get('direction')}/{c.get('horizon')} «{c.get('quote','')[:80]}»" for a, c in src.items())
        print(f"[{who}] {text}\n    -> {lab}\n")
    for a in set(gc) & set(pc):
        if gc[a]["direction"] != pc[a].get("direction") and kind in ("all", "dir"):
            print(f"[DIR {a}] gold={gc[a]['direction']} pred={pc[a].get('direction')} | {text}\n    gold«{gc[a]['quote'][:80]}» pred«{pc[a].get('quote','')[:80]}»\n")
        if gc[a]["horizon"] != pc[a].get("horizon") and kind in ("all", "hor"):
            print(f"[HOR {a}] gold={gc[a]['horizon']} pred={pc[a].get('horizon')} | {text}\n    gold«{gc[a]['quote'][:80]}»\n")
