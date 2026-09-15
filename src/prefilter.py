"""Regex prefilter: which tweets are worth an LLM call, and which assets they mention.

Bilingual (EN/TR). Deliberately loose on direction and strict on asset: a tweet must
name one of the three assets AND contain some directional/price vocabulary.
"""
from __future__ import annotations

import re

ASSETS = ("BTC", "GOLD", "SPX")

_ASSET_PATTERNS = {
    "BTC": re.compile(r"(?<![a-z0-9])(btc|bitcoin|bitcoi̇n)(?![a-z0-9])", re.I),
    "GOLD": re.compile(
        r"(?<![a-z0-9])(gold|xau|xauusd|gld)(?![a-z0-9])|(?<![a-zçğıöşü])alt[ıi]n(?![a-zçğöşü])",
        re.I,
    ),
    "SPX": re.compile(
        r"(?<![a-z0-9])(spx|spy|s&p ?500|s&p|sp500|es_f|nasdaq|ndx|qqq|nq_f|"
        r"wall ?street|us stocks?|us equit\w*)(?![a-z0-9])|"
        r"(abd|amerikan) (borsa|endeks)",
        re.I,
    ),
}

_DIRECTIONAL = re.compile(
    r"\b("
    # EN
    r"buy|sell|long|short|bull\w*|bear\w*|rally|crash|dump|pump|breakout|breakdown|"
    r"top|bottom|target|resistance|support|ath|all[- ]time high|correction|dip|"
    r"overbought|oversold|upside|downside|higher|lower|"
    # TR
    r"al[ıi]m|sat[ıi][şs]|al[ıi]n\w*|sat[ıi]n\w*|y[üu]ksel\w*|d[üu]ş\w*|dusus|"
    r"bo[ğg]a|ay[ıi]|zirve|dip|hedef|diren[çc]\w*|destek|ralli|[çc]ök\w*|"
    r"tepe|d[üu]zeltme|balon|ucuz|pahal[ıi]|toparlan\w*|kırıl\w*|kirilim"
    r")\b",
    re.I,
)

_PRICE_LIKE = re.compile(r"\$?\d{1,3}([.,]\d{3})+\b|\b\d+(\.\d+)?\s?[kK]\b|%\s?\d|\d\s?%")

_URL = re.compile(r"https?://\S+")


def detect_assets(text: str) -> list[str]:
    t = _URL.sub("", text)
    return [a for a in ASSETS if _ASSET_PATTERNS[a].search(t)]


def is_relevant(text: str, is_reply: bool = False) -> tuple[bool, list[str]]:
    """Return (relevant, assets).

    Any non-reply that names an asset goes to the LLM — the classifier decides whether it is
    a call. Directional vocabulary is too language/idiom-dependent to gate on (misses
    "Altın Pat-la-ya-cak!"), and an extra LLM call costs a fraction of a cent.
    Short replies (< 80 chars) are dropped: almost always pleasantries.
    """
    if is_reply and len(text) < 80:
        return False, []
    assets = detect_assets(text)
    return bool(assets), assets


def has_directional_hint(text: str) -> bool:
    """Diagnostic only: does the tweet carry obvious direction/price vocabulary?"""
    t = _URL.sub("", text)
    return bool(_DIRECTIONAL.search(t) or _PRICE_LIKE.search(t))
