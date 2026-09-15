"""Regex prefilter: which tweets mention one of the three assets (EN/TR), so they go to the LLM.

Deliberately generous: recall matters more than precision here — a false positive costs a fraction of a cent
at the classifier, a false negative is a lost call. The classifier decides what is actually a call.
"""
from __future__ import annotations

import html
import re

ASSETS = ("BTC", "GOLD", "SPX")

# Turkish letters that may appear inside a word; used for word boundaries instead of \b (which is ASCII-only)
_TR = "a-zA-Z0-9çğıöşüâîûÇĞİÖŞÜ"
_B0 = f"(?<![{_TR}])"   # left boundary (allows # $ @ prefixes)
_B1 = f"(?![{_TR}])"    # right boundary


def _alt(*terms: str) -> str:
    return "|".join(terms)


_ASSET_PATTERNS = {
    "BTC": re.compile(
        _B0 + "(" + _alt(
            r"btc", r"bitcoin\w*", r"bitcoi̇n\w*", r"xbt", r"sats", r"satoshi",  # bare "sat" = Turkish "sell"
            # TR: kripto / koin (crypto in general → BTC proxy), bitcoin'in etc. covered by \w*
            r"kripto\w*", r"koin\w*", r"coin\w*",
        ) + ")" + _B1, re.IGNORECASE),
    "GOLD": re.compile(
        _B0 + "(" + _alt(
            r"gold\w*", r"xau\w*", r"gld", r"gc1!?", r"gc=f", r"comex",
            # TR: altın (with suffixes: altının, altına, altında…), ons altın, gram altın, onsaltın, gramaltın
            r"alt[ıi]n\w*", r"ons ?alt[ıi]n\w*", r"gram ?alt[ıi]n\w*", r"ons",
            r"de[ğg]erli metal\w*", r"k[ıi]ymetli metal\w*", r"precious metals?", r"bullion",
        ) + ")" + _B1, re.IGNORECASE),
    "SPX": re.compile(
        _B0 + "(" + _alt(
            r"spx", r"spy", r"s&p ?500", r"s&p", r"s&amp;p ?500", r"s&amp;p", r"sp500", r"sp ?500", r"es_f", r"es1!?",
            r"nasdaq\w*", r"ndx", r"qqq", r"nq_f", r"dow\w*", r"djia", r"russell\w*", r"wall ?street",
            r"us ?stocks?", r"us ?equit\w*", r"us ?index(es)?", r"us500", r"nvidia", r"nvda", r"mag(nificent)? ?7",
            # TR: hisse (stock), borsa (exchange), endeks (index) — with suffixes; ABD/Amerikan borsaları
            r"hisse\w*", r"borsa\w*", r"endeks\w*", r"abd (borsa|endeks|hisse)\w*", r"amerikan (borsa|endeks|hisse)\w*",
            r"wall ?street", r"tekno(loji)? ?hisse\w*",
        ) + ")" + _B1, re.IGNORECASE),
}

# Turkish "borsa"/"hisse" alone often means BIST; only count them as SPX if a US cue is present in the tweet.
_TR_LOCAL_ONLY = re.compile(_B0 + r"(hisse\w*|borsa\w*|endeks\w*)" + _B1, re.IGNORECASE)
_US_CUE = re.compile(
    _B0 + r"(abd|amerika\w*|us|usa|wall ?street|s&p|s&amp;p|spx|spy|nasdaq\w*|dow\w*|nvidia|nvda|fed|fomc|"
    r"tesla|apple|microsoft|amazon|meta|google|alphabet|mag ?7|magnificent)" + _B1, re.IGNORECASE)
_BIST_CUE = re.compile(_B0 + r"(bist\w*|xu100|borsa istanbul|thy|aselsan|t[üu]pra[şs]|ko[çc]|garanti|akbank|ykb|"
                       r"ere[ğg]li|sasa|hekts|astor)" + _B1, re.IGNORECASE)

_URL = re.compile(r"https?://\S+")


def _clean(text: str) -> str:
    return _URL.sub("", html.unescape(text))


def detect_assets(text: str) -> list[str]:
    t = _clean(text)
    found = [a for a in ASSETS if _ASSET_PATTERNS[a].search(t)]
    if "SPX" in found:
        # if the only SPX evidence is generic TR market words, require a US cue and no BIST cue
        specific = re.sub(_TR_LOCAL_ONLY, "", t)
        if not _ASSET_PATTERNS["SPX"].search(specific):
            if _BIST_CUE.search(t) or not _US_CUE.search(t):
                found.remove("SPX")
    return found


def is_relevant(text: str, is_reply: bool = False) -> tuple[bool, list[str]]:
    """Return (relevant, assets). Any original tweet naming an asset is eligible for the classifier."""
    if is_reply:
        return False, []
    assets = detect_assets(text)
    return bool(assets), assets
