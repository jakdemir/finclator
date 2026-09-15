"""Generate roster.yaml from data/candidates_probed.csv: everyone who returned tweets, with tier + school guess."""
import csv

import yaml

SCHOOL_HINTS = [
    (("bitcoin", "btc", "crypto", "on-chain", "onchain", "hodl"), "Crypto"),
    (("gold", "silver", "precious", "altın", "gümüş", "sound money"), "Goldbug"),
    (("chart", "technical", "cmt", "trader", "trading", "swing", "levels"), "Technical"),
    (("quant", "data", "statistic", "flows", "research", "model"), "Quant"),
    (("macro", "economist", "iktisat", "ekonomi", "strategist", "fund", "cio", "investor", "yatırım"), "Macro"),
]
TR_HINT = ("türk", "istanbul", "ekonomi", "iktisat", "yatırım", "borsa", "piyasa", "hoca", "finans")


def guess_school(bio: str, existing: str) -> str:
    if existing:
        return existing
    b = bio.lower()
    for kws, school in SCHOOL_HINTS:
        if any(k in b for k in kws):
            return school
    return "Macro"


def guess_lang(bio: str, handle: str, existing: str) -> str:
    if existing:
        return existing
    b = bio.lower()
    return "tr" if any(k in b for k in TR_HINT) else "en"


rows = list(csv.DictReader(open("data/candidates_probed.csv")))
accounts = []
for r in rows:
    if int(r.get("probe_n") or 0) < 5:
        continue  # dead / suspended / no timeline
    h = r["handle"]
    accounts.append({
        "handle": h, "display_name": r.get("name") or h,
        "school": guess_school(r.get("bio", ""), r.get("school", "")),
        "language": guess_lang(r.get("bio", ""), h, r.get("lang", "")),
        "source": r["source"],
    })
accounts.sort(key=lambda a: a["handle"].lower())
yaml.safe_dump({"accounts": accounts}, open("roster.yaml", "w"), sort_keys=False, allow_unicode=True)
print(len(accounts), "accounts")
print({s: sum(a["school"] == s for a in accounts) for s in ("Macro", "Crypto", "Technical", "Goldbug", "Quant")})
