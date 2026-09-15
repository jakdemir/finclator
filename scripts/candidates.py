"""Finfluencer candidate list → data/candidates.csv

Sources: (1) accounts followed by --following USER, (2) SEED list below.
Per candidate, one /user/info call (+ optionally 2 timeline pages with --probe) gives:
  followers, statuses, age, bio, bio_score (asset/market keywords), and with --probe:
  originals/yr (2000/yr rule), prefilter hit-rate on the last ~40 originals (call density proxy).

Usage:
  PYTHONPATH=. .venv/bin/python scripts/candidates.py --following Jakdemir --probe
"""
from __future__ import annotations

import csv
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.fetch import _client, _get, _keep, _rate_per_year
from src.prefilter import detect_assets

OUT = Path("data/candidates.csv")

# (handle, school guess, lang)
SEED = [
    # Macro
    ("SantManukyan", "Macro", "tr"), ("LynAldenContact", "Macro", "en"), ("MacroAlf", "Macro", "en"),
    ("RaoulGMI", "Macro", "en"), ("jsblokland", "Macro", "en"), ("TaviCosta", "Macro", "en"),
    ("LukeGromen", "Macro", "en"), ("DiMartinoBooth", "Macro", "en"), ("biancoresearch", "Macro", "en"),
    ("hendry_hugh", "Macro", "en"), ("GameofTrades_", "Macro", "en"), ("EmreAlkin", "Macro", "tr"),
    ("atillayesilada", "Macro", "tr"), ("erkanoz", "Macro", "tr"), ("iriscibre", "Macro", "tr"),
    # Goldbug / hard money
    ("PeterSchiff", "Goldbug", "en"), ("LawrenceLepard", "Goldbug", "en"), ("KingKong9888", "Goldbug", "en"),
    ("goldtelegraph_", "Goldbug", "en"), ("TheGoldTelegraph", "Goldbug", "en"), ("Schuldensuehner", "Goldbug", "en"),
    ("islamicgoldking", "Goldbug", "tr"),
    # Technical
    ("laplace2011", "Technical", "tr"), ("PeterLBrandt", "Technical", "en"), ("GarethSoloway", "Technical", "en"),
    ("markminervini", "Technical", "en"), ("rektcapital", "Technical", "en"), ("CryptoCred", "Technical", "en"),
    ("ArtuncKocabalkan", "Technical", "tr"), ("SelcukGecer", "Technical", "tr"), ("kanaldfinans", "Technical", "tr"),
    ("TradingView", "Technical", "en"), ("Trader_XO", "Technical", "en"), ("CryptoCapo_", "Technical", "en"),
    # Crypto
    ("APompliano", "Crypto", "en"), ("woonomic", "Crypto", "en"), ("saylor", "Crypto", "en"),
    ("caprioleio", "Crypto", "en"), ("BTC_Archive", "Crypto", "en"), ("ki_young_ju", "Crypto", "en"),
    ("Ashcryptoreal", "Crypto", "en"), ("CryptoHayes", "Crypto", "en"), ("Pentosh1", "Crypto", "en"),
    ("davthewave", "Crypto", "en"), ("bitcoinlovekang", "Crypto", "tr"),
    # Quant / flows
    ("100trillionUSD", "Quant", "en"), ("KobeissiLetter", "Quant", "en"), ("zerohedge", "Quant", "en"),
    ("MacroCharts", "Quant", "en"), ("SoberLook", "Quant", "en"), ("charliebilello", "Quant", "en"),
    ("RyanDetrick", "Quant", "en"), ("GlobalMktObserv", "Quant", "en"), ("BarchartCrypto", "Quant", "en"),
    ("MichaelMOTTCM", "Quant", "en"), ("HedgeyeHQ", "Quant", "en"),
]

_BIO_KW = re.compile(
    r"\b(bitcoin|btc|crypto|gold|altın|macro|makro|trader|trading|investor|yatırım|portföy|hedge fund|"
    r"markets?|piyasa|borsa|s&p|equit|stocks?|fx|forex|strateji|strategist|analyst|analist|cio|cfa|"
    r"ekonomist|economist|fund manager|pm)\b", re.I)


def score_bio(bio: str) -> int:
    return len(set(m.lower() for m in _BIO_KW.findall(bio or "")))


def user_info(c, handle: str) -> dict | None:
    time.sleep(1.0)
    try:
        d = _get(c, "/twitter/user/info", userName=handle).get("data")
    except Exception as e:
        print(f"  {handle}: {e}", file=sys.stderr)
        return None
    if not d:
        return None
    created = d.get("createdAt")
    try:
        cdt = datetime.fromisoformat(created.replace("Z", "+00:00")) if "T" in created else \
            datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        cdt = None
    age = (datetime.now(timezone.utc) - cdt).days / 365 if cdt else 0
    return {
        "handle": d.get("userName", handle), "name": d.get("name"), "followers": d.get("followers", 0),
        "statuses": d.get("statusesCount", 0), "age_y": round(age, 1),
        "statuses_per_y": round(d.get("statusesCount", 0) / age) if age else 0,
        "bio": (d.get("description") or "").replace("\n", " "), "bio_score": score_bio(d.get("description") or ""),
        "verified": d.get("isBlueVerified"),
    }


def probe(c, handle: str) -> dict:
    tweets, cursor = [], ""
    for _ in range(2):
        time.sleep(1.0)
        r = _get(c, "/twitter/user/last_tweets", userName=handle, cursor=cursor, includeReplies="false")
        page = [t for t in (r.get("data") or {}).get("tweets") or [] if _keep(t)]
        tweets += page
        if not r.get("has_next_page") or not page:
            break
        cursor = r["next_cursor"]
    n = len(tweets)
    hits = sum(1 for t in tweets if detect_assets(t.get("text", "")))
    return {"originals_per_y": round(_rate_per_year(tweets)) if n > 1 else 0,
            "asset_hit_rate": round(hits / n, 2) if n else 0, "probe_n": n,
            "last_tweet": tweets[0]["createdAt"][:16] if tweets else ""}


def followings(c, user: str) -> list[dict]:
    out, cursor = [], ""
    while True:
        time.sleep(1.0)
        r = _get(c, "/twitter/user/followings", userName=user, cursor=cursor, pageSize=200)
        out += r.get("followings") or []
        if not r.get("has_next_page") or not r.get("next_cursor"):
            break
        cursor = r["next_cursor"]
    return out


def main():
    args = sys.argv[1:]
    do_probe = "--probe" in args
    following_user = args[args.index("--following") + 1] if "--following" in args else None

    rows: dict[str, dict] = {}
    for h, school, lang in SEED:
        rows[h.lower()] = {"handle": h, "source": "seed", "school": school, "lang": lang}

    with _client() as c:
        if following_user:
            print(f"fetching followings of @{following_user}…", flush=True)
            for f in followings(c, following_user):
                h = f.get("userName", "")
                if not h:
                    continue
                key = h.lower()
                r = rows.setdefault(key, {"handle": h, "source": "following", "school": "", "lang": ""})
                if r["source"] == "seed":
                    r["source"] = "seed+following"
                r.update({"name": f.get("name"), "followers": f.get("followers_count", f.get("followers", 0)),
                          "statuses": f.get("statuses_count", f.get("statusesCount", 0)),
                          "bio": (f.get("description") or "").replace("\n", " "),
                          "bio_score": score_bio(f.get("description") or "")})
            print(f"  {sum(1 for r in rows.values() if 'following' in r['source'])} followings", flush=True)

        for key, r in rows.items():
            if "followers" not in r:  # seed accounts not covered by followings
                info = user_info(c, r["handle"])
                if info:
                    r.update(info)
            if do_probe and (r.get("bio_score", 0) >= 1 or r["source"] != "following"):
                print(f"  probing {r['handle']}", flush=True)
                try:
                    r.update(probe(c, r["handle"]))
                except Exception as e:
                    print(f"  {r['handle']}: {e}", file=sys.stderr)

    cols = ["handle", "source", "school", "lang", "name", "followers", "statuses", "age_y", "statuses_per_y",
            "originals_per_y", "asset_hit_rate", "probe_n", "last_tweet", "bio_score", "verified", "bio"]
    ordered = sorted(rows.values(), key=lambda r: (-(r.get("asset_hit_rate") or 0), -(r.get("bio_score") or 0),
                                                  -(r.get("followers") or 0)))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(ordered)
    print(f"wrote {OUT} ({len(ordered)} candidates)")


if __name__ == "__main__":
    main()
