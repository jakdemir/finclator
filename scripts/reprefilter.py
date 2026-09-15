"""Re-run the prefilter over all stored tweets (after changing prefilter rules). Never touches classified tweets' calls;
newly-relevant tweets become pending for the classifier."""
from src.db import connect
from src.prefilter import is_relevant

conn = connect()
rows = conn.execute("SELECT id, text, relevant, assets_hint FROM tweets").fetchall()
changed = newly = 0
for r in rows:
    rel, assets = is_relevant(r["text"], False)
    hint = ",".join(assets)
    if int(rel) != r["relevant"] or hint != r["assets_hint"]:
        conn.execute("UPDATE tweets SET relevant=?, assets_hint=? WHERE id=?", (int(rel), hint, r["id"]))
        changed += 1
        if rel and not r["relevant"]:
            newly += 1
conn.commit()
tot, rel, pend = conn.execute("SELECT count(*), sum(relevant), sum(relevant AND NOT classified) FROM tweets").fetchone()
print(f"{len(rows)} tweets, {changed} changed, {newly} newly relevant → {rel}/{tot} relevant, {pend} pending classification")
for r in conn.execute("SELECT assets_hint, count(*) FROM tweets WHERE relevant=1 GROUP BY 1 ORDER BY 2 DESC"):
    print("  ", tuple(r))
