"""Admin page: live progress, matrix, trust and audit — reads SQLite on every request.

    python -m src.admin            # http://127.0.0.1:8787
    python -m src.admin --port N
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import audit
from .db import LOG_PATH as LOG
from .db import connect
from .models import active_model

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ("BTC", "GOLD", "SPX")
HORIZONS = ("SHORT", "MEDIUM", "LONG")

CSS = """
body{font:14px system-ui,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}
nav{display:flex;gap:18px;padding:10px 18px;background:#181b22;border-bottom:1px solid #2a2f3a;position:sticky;top:0}
nav a{color:#9ecbff;text-decoration:none}nav a.on{color:#fff;font-weight:600}
main{padding:18px;max-width:1500px}
h2{margin:22px 0 8px;font-size:16px}
.cards{display:flex;flex-wrap:wrap;gap:10px}
.card{background:#181b22;border:1px solid #2a2f3a;border-radius:8px;padding:10px 14px;min-width:130px}
.card b{display:block;font-size:20px}.card small{color:#9aa}
table{border-collapse:collapse;font-size:13px}th,td{border:1px solid #2a2f3a;padding:4px 8px;text-align:left}
th{background:#1d2129;cursor:pointer}td.num{text-align:right;font-variant-numeric:tabular-nums}
.grid td{text-align:center;font-weight:700;width:120px;height:52px}
.BUY{background:#1e6b3a}.SELL{background:#7a2323}.NEUTRAL{background:#444}.NA{background:#222;color:#888}
.bar{height:8px;background:#2a2f3a;border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:#4c9aff}
.ok{color:#7ddc8a}.warn{color:#f0b64c}.err{color:#ff6b6b}
pre{background:#0a0c10;padding:10px;border-radius:6px;max-height:340px;overflow:auto;font-size:12px}
.mono{font-family:ui-monospace,monospace}
"""

JS = """
document.addEventListener('click',e=>{const th=e.target.closest('th');if(!th||!th.closest('table.sortable'))return;
const t=th.closest('table'),i=[...th.parentNode.children].indexOf(th),tb=t.tBodies[0],asc=th.dataset.asc!=='1';
th.dataset.asc=asc?'1':'0';const v=td=>td.dataset.v!==undefined?+td.dataset.v:(isNaN(parseFloat(td.textContent))?td.textContent:parseFloat(td.textContent));
[...tb.rows].sort((a,b)=>{const x=v(a.cells[i]),y=v(b.cells[i]);return (x>y?1:x<y?-1:0)*(asc?1:-1)}).forEach(r=>tb.appendChild(r));});
async function tailLog(){const el=document.getElementById('log');if(!el)return;
 try{const t=await (await fetch('/api/log')).text();if(t!==el.textContent){el.textContent=t;
 if(document.getElementById('follow').checked)el.scrollTop=el.scrollHeight;}}catch(e){}}
window.addEventListener('load',()=>{const el=document.getElementById('log');if(el){el.scrollTop=el.scrollHeight;setInterval(tailLog,3000);}});
"""


def _q(conn, sql, *a):
    return conn.execute(sql, a).fetchall()


def _one(conn, sql, *a):
    return conn.execute(sql, a).fetchone()


def _proc_running(pattern: str) -> bool:
    out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True).stdout
    return bool(out.strip())


_credits_cache: dict = {"t": 0.0, "v": None}


def _credits() -> float | None:
    """twitterapi.io balance in USD, cached 5 min (1 USD = 100,000 credits)."""
    import os
    import time
    import urllib.request
    if time.time() - _credits_cache["t"] < 300:
        return _credits_cache["v"]
    key = os.environ.get("TWITTERAPI_IO_KEY")
    if not key and (ROOT / ".env").exists():
        key = next((ln.split("=", 1)[1].strip() for ln in (ROOT / ".env").read_text().splitlines()
                    if ln.startswith("TWITTERAPI_IO_KEY=")), None)
    v = None
    if key:
        try:
            req = urllib.request.Request("https://api.twitterapi.io/oapi/my/info", headers={"X-API-Key": key})
            info = json.load(urllib.request.urlopen(req, timeout=10))
            v = (info.get("recharge_credits", 0) + info.get("bonus_credits", 0)) / 100_000
        except Exception:  # noqa: BLE001
            v = None
    _credits_cache.update(t=time.time(), v=v)
    return v


def _log_tail(n=200) -> str:
    """Tail of data/pipeline.log; the legacy backfill.log (no timestamps) is shown until it disappears."""
    out = []
    legacy = ROOT / "data" / "backfill.log"
    if legacy.exists():
        out += ["# backfill.log (legacy, untimestamped, mtime %s UTC)" % datetime.fromtimestamp(legacy.stat().st_mtime, timezone.utc).strftime("%H:%M:%S")]
        out += legacy.read_text(errors="replace").splitlines()[-n:]
    if LOG.exists():
        out += LOG.read_text(errors="replace").splitlines()[-n:]
    return "\n".join(out[-n:])


def _page(title: str, body: str, active: str) -> str:
    tabs = [("/", "Progress"), ("/matrix", "Matrix"), ("/accounts", "Accounts"), ("/audit", "Audit"), ("/architecture", "Architecture"), ("/tables", "Tables"), ("/api/status", "JSON")]
    nav = "".join(f"<a href='{h}' class='{'on' if h == active else ''}'>{t}</a>" for h, t in tabs)
    refresh = "" if active in ("/tables", "/audit") else f"<meta http-equiv=refresh content={60 if active == '/' else 30}>"
    return (f"<!doctype html><meta charset=utf-8><title>Finclator admin — {title}</title>"
            f"{refresh}<style>{CSS}</style><script>{JS}</script>"
            f"<nav>{nav}<span style='margin-left:auto;color:#9aa'>{datetime.now(timezone.utc):%H:%M:%S} UTC · {'page 60s · log live 3s' if active == '/' else ('no auto-refresh' if active in ('/tables', '/audit') else 'auto-refresh 30s')}</span></nav>"
            f"<main>{body}</main>")


def status(conn) -> dict:
    f = _one(conn, """SELECT count(*) t, coalesce(sum(relevant),0) rel, coalesce(sum(relevant AND classified),0) cls,
                       coalesce(sum(is_reply),0) replies, coalesce(sum(text LIKE 'RT @%'),0) rts,
                       (SELECT count(*) FROM calls) calls, (SELECT count(*) FROM outcomes) outs,
                       (SELECT count(*) FROM trust WHERE asset='*' AND horizon='*') scored,
                       (SELECT count(*) FROM accounts) accounts,
                       (SELECT count(*) FROM accounts WHERE active) active,
                       (SELECT count(DISTINCT handle) FROM tweets) fetched FROM tweets""")
    prices = {r["asset"]: dict(r) for r in _q(conn, "SELECT asset, min(date) a, max(date) b, count(*) n FROM prices GROUP BY asset")}
    matrix_p = ROOT / "data" / "matrix.json"
    matrix = json.loads(matrix_p.read_text()) if matrix_p.exists() else {}
    return {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backfill_running": _proc_running("scripts/backfill.py"),
        "run_running": _proc_running("src.run"),
        "tweets": f["t"], "relevant": f["rel"], "classified": f["cls"], "pending_classification": f["rel"] - f["cls"],
        "replies_in_db": f["replies"], "retweets_in_db": f["rts"],
        "calls": f["calls"], "outcomes": f["outs"], "accounts": f["accounts"], "accounts_active": f["active"],
        "accounts_fetched": f["fetched"], "accounts_scored": f["scored"],
        "prices": prices, "matrix_generated_at": matrix.get("generated_at"),
        "matrix": {k: v.get("label") for k, v in matrix.get("cells", {}).items()},
    }


def page_progress(conn) -> str:
    s = status(conn)
    e = html.escape
    pct = lambda a, b: (100 * a / b) if b else 0  # noqa: E731
    run_state = ("<span class=ok>running</span>" if s["backfill_running"] else "<span class=warn>idle</span>")
    cards = [
        ("backfill", run_state, "scripts/backfill.py"),
        ("accounts fetched", f"{s['accounts_fetched']} / {s['accounts']}", f"{s['accounts_active']} active"),
        ("tweets", f"{s['tweets']:,}", f"replies {s['replies_in_db']} · RTs {s['retweets_in_db']} (must be 0)"),
        ("asset-mentioning", f"{s['relevant']:,}", f"{pct(s['relevant'], s['tweets']):.0f}% of tweets"),
        ("classified", f"{s['classified']:,}", f"<span class='{'warn' if s['pending_classification'] else 'ok'}'>{s['pending_classification']:,} pending</span>"),
        ("calls", f"{s['calls']:,}", f"{s['outcomes']:,} matured & evaluated"),
        ("accounts scored", f"{s['accounts_scored']}", "have ≥1 matured outcome"),
    ]
    cr = _credits()
    if cr is not None:
        cards.append(("twitterapi.io", f"${cr:.2f}", f"≈ {int(cr * 100_000 / 15):,} tweets left"))
    B = ["<h2>Pipeline</h2><div class=cards>"]
    for t, v, sub in cards:
        B.append(f"<div class=card><small>{t}</small><b>{v}</b><small>{sub}</small></div>")
    B.append("</div>")
    B.append(f"<h2>Fetch coverage <small>({pct(s['accounts_fetched'], s['accounts']):.0f}%)</small></h2>"
             f"<div class=bar><i style='width:{pct(s['accounts_fetched'], s['accounts']):.1f}%'></i></div>")
    B.append(f"<h2>Classification <small>({pct(s['classified'], s['relevant']):.0f}%)</small></h2>"
             f"<div class=bar><i style='width:{pct(s['classified'], s['relevant']):.1f}%'></i></div>")

    B.append("<h2>Prices</h2><table><tr><th>asset</th><th>from</th><th>to</th><th>rows</th><th>last close</th><th>age</th></tr>")
    today = datetime.now(timezone.utc).date()
    for a in ASSETS:
        p = s["prices"].get(a)
        if not p:
            B.append(f"<tr><td>{a}</td><td colspan=5 class=err>no data</td></tr>")
            continue
        last = _one(conn, "SELECT close FROM prices WHERE asset=? ORDER BY date DESC LIMIT 1", a)[0]
        age = (today - datetime.strptime(p["b"], "%Y-%m-%d").date()).days
        cls = "ok" if age <= 4 else "warn"
        B.append(f"<tr><td>{a}</td><td>{p['a']}</td><td>{p['b']}</td><td class=num>{p['n']}</td>"
                 f"<td class=num>{last:,.2f}</td><td class={cls}>{age}d</td></tr>")
    B.append("</table>")

    B.append("<h2>Per-account fetch</h2><table class=sortable><thead><tr><th>account</th><th>school</th><th>sampling</th>"
             "<th>orig/yr</th><th>tweets</th><th>relevant</th><th>classified</th><th>calls</th><th>first</th><th>last</th></tr></thead><tbody>")
    for r in _q(conn, """SELECT a.handle, a.school, a.sampling, a.rate_per_year, a.active,
                (SELECT count(*) FROM tweets t WHERE t.handle=a.handle) n,
                (SELECT coalesce(sum(relevant),0) FROM tweets t WHERE t.handle=a.handle) rel,
                (SELECT coalesce(sum(relevant AND classified),0) FROM tweets t WHERE t.handle=a.handle) cls,
                (SELECT count(*) FROM calls c WHERE c.handle=a.handle) calls,
                (SELECT min(created_at) FROM tweets t WHERE t.handle=a.handle) f,
                (SELECT max(created_at) FROM tweets t WHERE t.handle=a.handle) l
                FROM accounts a ORDER BY n DESC"""):
        cls = "" if r["n"] else " class=warn"
        B.append(f"<tr><td{cls}>@{e(r['handle'])}{'' if r['active'] else ' <small>(inactive)</small>'}</td><td>{e(r['school'] or '')}</td>"
                 f"<td>{e(r['sampling'] or 'full')}</td><td class=num>{r['rate_per_year'] or ''}</td>"
                 f"<td class=num>{r['n']}</td><td class=num>{r['rel']}</td><td class=num>{r['cls']}</td><td class=num>{r['calls']}</td>"
                 f"<td>{(r['f'] or '')[:10]}</td><td>{(r['l'] or '')[:10]}</td></tr>")
    B.append("</tbody></table>")

    B.append("<h2>pipeline.log <small>(live, last 200 lines, UTC) · <label><input type=checkbox id=follow checked> follow</label></small></h2>"
             f"<pre id=log>{e(_log_tail())}</pre>")
    return _page("progress", "".join(B), "/")


def page_matrix(conn) -> str:
    e = html.escape
    B = []
    matrix_p = ROOT / "data" / "matrix.json"
    m = json.loads(matrix_p.read_text()) if matrix_p.exists() else {"generated_at": "", "cells": {}}
    B.append(f"<h2>Current matrix <small>generated {e(m.get('generated_at') or '—')}</small> "
             f"<a href='/matrix?rebuild=1' style='color:#9ecbff'>rebuild now</a></h2>")
    B.append("<table class=grid><tr><th></th><th>SHORT<br><small>0–3 mo</small></th><th>MEDIUM<br><small>3–12 mo</small></th><th>LONG<br><small>1–5 y</small></th></tr>")
    for a in ASSETS:
        tds = ""
        for h in HORIZONS:
            c = m["cells"].get(f"{a}:{h}", {"label": "N/A", "n_calls": 0, "net": 0, "buy": 0, "sell": 0, "neutral": 0})
            cls = c["label"] if c["label"] != "N/A" else "NA"
            w = c.get("buy", 0) + c.get("sell", 0) + c.get("neutral", 0)
            tds += f"<td class={cls}>{c['label']}<br><small>n={c['n_calls']} net={c['net']:+.2f} w={w:.2f}</small></td>"
        B.append(f"<tr><th>{a}</th>{tds}</tr>")
    B.append("</table>")

    B.append("<h2>Contributions per cell <small>(weight = trust × confidence × recency)</small></h2>")
    for a in ASSETS:
        for h in HORIZONS:
            c = m["cells"].get(f"{a}:{h}")
            if not c or not c.get("contributors"):
                continue
            sch = " · ".join(f"{k}: {v['label']}" for k, v in c.get("schools", {}).items())
            B.append(f"<details><summary><b>{a} {h}</b> — {c['label']} (n={c['n_calls']}) <small>{e(sch)}</small></summary><table class=sortable><thead><tr>"
                     "<th>account</th><th>direction</th><th>called</th><th>weight</th><th>quote</th><th>tweet</th></tr></thead><tbody>")
            for x in c["contributors"]:
                B.append(f"<tr><td>@{e(x['handle'])}</td><td class={x['direction']}>{x['direction']}</td><td>{x['date']}</td>"
                         f"<td class=num>{x['weight']:.3f}</td><td><small>{e(x.get('quote') or '')}</small></td>"
                         f"<td><a href='https://x.com/{e(x['handle'])}/status/{x['tweet_id']}' style='color:#9ecbff'>↗</a></td></tr>")
            B.append("</tbody></table></details>")

    B.append("<h2>Trust by school</h2><table class=sortable><thead><tr><th>school</th><th>accounts</th><th>scored</th><th>mean trust</th><th>Σn</th></tr></thead><tbody>")
    for r in _q(conn, """SELECT a.school, count(*) n_acc, count(t.score) scored, avg(t.score) mean, coalesce(sum(t.n),0) sn
                          FROM accounts a LEFT JOIN trust t ON t.handle=a.handle AND t.asset='*' AND t.horizon='*' AND t.model=?
                          GROUP BY a.school ORDER BY mean DESC""", active_model()):
        B.append(f"<tr><td>{e(r['school'] or '')}</td><td class=num>{r['n_acc']}</td><td class=num>{r['scored']}</td>"
                 f"<td class=num>{(r['mean'] or 0):.3f}</td><td class=num>{r['sn']}</td></tr>")
    B.append("</tbody></table>")
    return _page("matrix", "".join(B), "/matrix")


def page_accounts(conn) -> str:
    e = html.escape
    model = active_model()
    trust = {(r["handle"], r["asset"], r["horizon"]): r for r in _q(conn, "SELECT * FROM trust WHERE model=?", model)}

    def tc(h, a, hz="*"):
        r = trust.get((h, a, hz))
        return f"<td class=num data-v={r['score'] if r else 0.5}>{r['score']:.2f}<small> n={r['n']}</small></td>" if r else "<td class=num data-v=0.5><small>–</small></td>"

    B = [f"<h2>Trust scores <small>(shrunk toward 0.5; n = matured outcomes) · model {e(model)}</small></h2>",
         "<table class=sortable><thead><tr><th>account</th><th>school</th><th>calls</th><th>n</th><th>hits</th><th>overall</th>",
         "<th>BTC</th><th>GOLD</th><th>SPX</th><th>SHORT</th><th>MEDIUM</th><th>LONG</th></tr></thead><tbody>"]
    for r in _q(conn, """SELECT a.handle, a.school, (SELECT count(*) FROM calls c WHERE c.handle=a.handle AND c.model=?) calls FROM accounts a""", model):
        ov = trust.get((r["handle"], "*", "*"))
        B.append(f"<tr><td><a href='https://x.com/{e(r['handle'])}' style='color:#9ecbff'>@{e(r['handle'])}</a></td><td>{e(r['school'] or '')}</td><td class=num>{r['calls']}</td>")
        if ov:
            B.append(f"<td class=num>{ov['n']}</td><td class=num>{ov['correct']:.1f}</td><td class=num data-v={ov['score']}><b>{ov['score']:.3f}</b></td>")
        else:
            B.append("<td class=num>0</td><td></td><td class=num data-v=0.5><small>0.500 prior</small></td>")
        B.append(tc(r["handle"], "BTC") + tc(r["handle"], "GOLD") + tc(r["handle"], "SPX")
                 + tc(r["handle"], "*", "SHORT") + tc(r["handle"], "*", "MEDIUM") + tc(r["handle"], "*", "LONG") + "</tr>")
    B.append("</tbody></table>")
    return _page("accounts", "".join(B), "/accounts")


def page_architecture(conn) -> str:
    from .evaluate import MATURITY_DAYS
    from .prefilter import _ASSET_PATTERNS
    e = html.escape
    f = _one(conn, """SELECT count(*) t, coalesce(sum(relevant),0) rel, coalesce(sum(relevant AND classified),0) cls,
                       (SELECT count(*) FROM calls) calls, (SELECT count(DISTINCT tweet_id) FROM calls) ct,
                       (SELECT count(*) FROM outcomes) outs, (SELECT count(*) FROM accounts) acc FROM tweets""")
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "–"  # noqa: E731
    B = ["<h2>Data flow</h2><pre class=mono>"
         f"""twitterapi.io ──► fetch.py ──────────► tweets            {f['t']:>8,}  originals only (replies / RTs rejected at insert)
                    {f['acc']} accounts, 3y   │                       full timeline ≤1,000 orig/yr, else days 1–3 of each month
                                    ▼
                     prefilter.py  regex, free ──► relevant=1    {f['rel']:>8,}  ({pct(f['rel'], f['t'])})  "mentions BTC / GOLD / SPX at all?"
                                    ▼
                     classify.py   LLM, $ ──────► classified=1  {f['cls']:>8,}  ({pct(f['cls'], f['rel'])} of relevant)  "explicit, falsifiable call?"
                                    │                calls          {f['calls']:>8,}  from {f['ct']:,} tweets
                                    ▼
   Yahoo daily ─► prices.py ─► evaluate.py ─────► outcomes        {f['outs']:>8,}  matured calls only
                                    ▼
                     score.py      trust per (account, asset, horizon), shrunk toward 0.5
                                    ▼
                     matrix.py     3×3 = Σ trust × confidence × recency-decay  ─► data/matrix.json
                                    ▼
                     audit.py · admin.py · pine.py (verification page, this site, TradingView indicator)"""
         "</pre>"]

    B.append("<h2>Stage 1 — prefilter <small>(src/prefilter.py) · generous: recall over precision</small></h2>"
             "<p>Pure regex, EN+TR. Text is HTML-unescaped and URLs stripped first. Word boundaries are Turkish-aware "
             "(Python's <code>\\b</code> is ASCII-only, so <i>altının</i> would otherwise never match). A false positive costs a fraction "
             "of a cent at stage 2; a false negative is a lost call forever.</p><table><tr><th>asset</th><th>pattern (live from code)</th></tr>")
    for a in ASSETS:
        B.append(f"<tr><td>{a}</td><td class=mono><small>{e(_ASSET_PATTERNS[a].pattern)}</small></td></tr>")
    B.append("</table><p>Disambiguation: <i>hisse / borsa / endeks</i> alone usually means BIST, so they count as SPX only with a "
             "US cue (ABD, Fed, Nasdaq, Tesla…) <b>and</b> no BIST cue (THY, Aselsan, xu100…). "
             "Result is stored as <code>tweets.relevant</code> + <code>assets_hint</code>. "
             "Check it on <a href='/audit' style='color:#9ecbff'>Audit → “prefilter dropped”</a> sample.</p>")

    B.append("<h2>Stage 2 — classifier <small>(src/classify.py) · strict</small></h2>"
             "<p>One LLM call per relevant tweet. Must answer “is this an explicit, falsifiable call?” — past-move reports, news, charts "
             "without opinion, generic macro talk → <code>is_call=false</code>. Per asset it returns direction (BUY/SELL/NEUTRAL), horizon, "
             "confidence, price target in USD, and an <b>exact quote</b> from the tweet that justifies the label (auditable). "
             "Two modes with the same schema: <code>ANTHROPIC_API_KEY</code> for the cron, or export-JSONL → label interactively → import "
             "(tagged in <code>calls.model</code>).</p>"
             "<table><tr><th>horizon</th><th>meaning (spec)</th><th>evaluated after</th><th>inferred when unstated</th></tr>"
             f"<tr><td>SHORT</td><td>0–3 months</td><td>{MATURITY_DAYS['SHORT']} d</td><td>technical / level talk, swing</td></tr>"
             f"<tr><td>MEDIUM</td><td>3–12 months</td><td>{MATURITY_DAYS['MEDIUM']} d</td><td>default</td></tr>"
             f"<tr><td>LONG</td><td>1–5 years</td><td>{MATURITY_DAYS['LONG']} d</td><td>macro / structural / cycle thesis</td></tr></table>")

    B.append("<h2>Evaluation, trust, matrix</h2><ul>"
             "<li><b>Prices</b>: Yahoo daily close — BTC-USD, GC=F (COMEX front month), ^GSPC — stored in <code>prices</code> from 2020.</li>"
             "<li><b>Outcome</b>: return from entry close to exit close at maturity vs a flat band of 0.5σ·√days (trailing-1y daily vol). "
             "CORRECT=1, PARTIAL (predicted move, market flat)=0.5, WRONG=0. Price target: +0.25 if any close touched it within the horizon, −0.25 if not.</li>"
             "<li><b>Trust</b> = (Σhits + 5) / (n + 10) per (account, asset, horizon); fallbacks specific → asset → overall → 0.5 prior. "
             "Point-in-time: only outcomes matured by the as-of date count, so history never sees the future.</li>"
             "<li><b>Matrix</b>: per cell, each call in the window weighs trust × confidence × 2<sup>−age/(window/3)</sup>; "
             "net = (buy−sell)/total → BUY &gt; +0.15, SELL &lt; −0.15, else NEUTRAL; N/A when total weight &lt; 0.3. "
             "Everyone contributes; noisy accounts are outweighed, not filtered.</li>"
             "<li><b>Schools</b> (accounts.school) get their own sub-label per cell, shown on <a href='/matrix' style='color:#9ecbff'>Matrix</a>.</li></ul>")

    B.append("<h2>Known weak spots</h2><ul>"
             "<li>Stage 1 can't catch calls that name no asset (“this is the top” under a chart image).</li>"
             "<li>Horizon inference on terse Turkish tweets is the least reliable field.</li>"
             "<li>Stage 2 API path is untested at scale; only the interactive labels exist so far.</li>"
             "<li>Sampled accounts (&gt;1,000 orig/yr) see ~10% of their tweets — evenly spread, but sparse.</li></ul>")

    B.append("<h2>Files</h2><table><tr><th>file</th><th>role</th></tr>"
             "<tr><td class=mono>roster.yaml</td><td>accounts, school, language</td></tr>"
             "<tr><td class=mono>src/db.py</td><td>SQLite schema (accounts, tweets, calls, outcomes, prices, trust), log()</td></tr>"
             "<tr><td class=mono>src/fetch.py</td><td>twitterapi.io: since_id incremental, 3y backfill, monthly sampling windows</td></tr>"
             "<tr><td class=mono>src/prefilter.py</td><td>stage 1</td></tr><tr><td class=mono>src/classify.py</td><td>stage 2</td></tr>"
             "<tr><td class=mono>src/prices.py · evaluate.py · score.py · matrix.py</td><td>outcomes → trust → 3×3</td></tr>"
             "<tr><td class=mono>src/audit.py · admin.py · pine.py</td><td>verification page, this site, TradingView script</td></tr>"
             "<tr><td class=mono>src/run.py</td><td>weekly: fetch → classify → prices → evaluate → score → matrix → audit → pine</td></tr>"
             "<tr><td class=mono>scripts/backfill.py</td><td>parallel 3y backfill (8 workers)</td></tr></table>")
    return _page("architecture", "".join(B), "/architecture")


def _render_rows(cur, limit_cell=160) -> str:
    e = html.escape
    cols = [d[0] for d in cur.description]
    out = ["<table class=sortable><thead><tr>" + "".join(f"<th>{e(c)}</th>" for c in cols) + "</tr></thead><tbody>"]
    for r in cur:
        tds = ""
        for c, v in zip(cols, r, strict=True):
            if v is None:
                tds += "<td><small>∅</small></td>"
            elif isinstance(v, (int, float)):
                tds += f"<td class=num>{v:,}</td>" if isinstance(v, int) else f"<td class=num>{v:.4g}</td>"
            else:
                s = str(v)
                cell = e(s[:limit_cell]) + ("…" if len(s) > limit_cell else "")
                if c == "tweet_id" or (c == "id" and cols and "text" in cols):
                    h = r[cols.index("handle")] if "handle" in cols else ""
                    cell = f"<a href='https://x.com/{e(h)}/status/{e(s)}' style='color:#9ecbff'>{e(s)}</a>"
                tds += f"<td title='{e(s[:800])}'>{cell}</td>"
        out.append(f"<tr>{tds}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def page_tables(conn, qs: str) -> str:
    from urllib.parse import parse_qs
    e = html.escape
    q = parse_qs(qs)
    name = q.get("t", [""])[0]
    offset = max(0, int(q.get("o", ["0"])[0] or 0))
    limit = min(500, max(1, int(q.get("n", ["50"])[0] or 50)))
    sql = q.get("sql", [""])[0].strip()
    tables = [r[0] for r in _q(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]

    B = ["<h2>Tables</h2><table><tr><th>table</th><th>rows</th><th>columns</th></tr>"]
    for t in tables:
        n = _one(conn, f"SELECT count(*) FROM {t}")[0]
        cols = ", ".join(r["name"] + ("*" if r["pk"] else "") for r in _q(conn, f"PRAGMA table_info({t})"))
        B.append(f"<tr><td><a href='/tables?t={t}' style='color:#9ecbff'><b>{t}</b></a></td><td class=num>{n:,}</td><td><small>{e(cols)}</small></td></tr>")
    B.append("</table>")

    B.append("<h2>SQL <small>(read-only; SELECT / WITH / EXPLAIN only, 500 rows max)</small></h2>"
             f"<form method=get action=/tables><textarea name=sql rows=3 style='width:100%;max-width:900px;background:#0a0c10;color:#e6e6e6;border:1px solid #2a2f3a;padding:6px;font-family:ui-monospace,monospace'>{e(sql)}</textarea><br>"
             "<button style='margin-top:6px'>run</button> "
             "<small style='color:#9aa'>examples: <code>SELECT handle, count(*) n FROM calls GROUP BY 1 ORDER BY 2 DESC</code> · "
             "<code>SELECT * FROM outcomes WHERE result='WRONG'</code> · <code>SELECT date, close FROM prices WHERE asset='BTC' ORDER BY date DESC LIMIT 10</code></small></form>")
    if sql:
        first = sql.lstrip("(").split(None, 1)[0].upper() if sql else ""
        if first not in ("SELECT", "WITH", "EXPLAIN", "PRAGMA") or ";" in sql.rstrip(";"):
            B.append("<p class=err>only a single SELECT / WITH / EXPLAIN / PRAGMA statement is allowed</p>")
        else:
            try:
                ro = connect()
                ro.execute("PRAGMA query_only=1")
                cur = ro.execute(sql.rstrip(";") + (" LIMIT 500" if first == "SELECT" and " LIMIT " not in sql.upper() else ""))
                B.append("<h3>result</h3>" + _render_rows(cur))
                ro.close()
            except Exception as ex:  # noqa: BLE001
                B.append(f"<p class=err>{e(str(ex))}</p>")

    if name in tables:
        total = _one(conn, f"SELECT count(*) FROM {name}")[0]
        order = {"tweets": "created_at DESC", "calls": "called_at DESC", "outcomes": "exit_date DESC", "prices": "date DESC",
                 "trust": "score DESC", "accounts": "handle"}.get(name, "rowid")
        cur = conn.execute(f"SELECT * FROM {name} ORDER BY {order} LIMIT ? OFFSET ?", (limit, offset))
        prev_ = f"<a href='/tables?t={name}&o={max(0, offset - limit)}&n={limit}' style='color:#9ecbff'>← prev</a>" if offset else ""
        next_ = f"<a href='/tables?t={name}&o={offset + limit}&n={limit}' style='color:#9ecbff'>next →</a>" if offset + limit < total else ""
        B.append(f"<h2>{name} <small>rows {offset + 1:,}–{min(offset + limit, total):,} of {total:,} · order {e(order)} · "
                 f"{prev_} {next_} · <a href='/tables?t={name}&o={offset}&n=200' style='color:#9ecbff'>200/page</a></small></h2>")
        B.append(_render_rows(cur))
    return _page("tables", "".join(B), "/tables")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 — quiet
        pass

    def _send(self, body: str, ctype="text/html; charset=utf-8", code=200):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path, _, qs = self.path.partition("?")
        conn = connect()
        try:
            if path == "/":
                self._send(page_progress(conn))
            elif path == "/matrix":
                if "rebuild=1" in qs:
                    from .matrix import build as build_matrix
                    from .score import recompute
                    recompute(conn)
                    build_matrix(conn)
                    self.send_response(302)
                    self.send_header("Location", "/matrix")
                    self.end_headers()
                    return
                self._send(page_matrix(conn))
            elif path == "/accounts":
                self._send(page_accounts(conn))
            elif path == "/tables":
                self._send(page_tables(conn, qs))
            elif path == "/architecture":
                self._send(page_architecture(conn))
            elif path == "/audit":
                self._send(audit.render())
            elif path == "/api/log":
                self._send(_log_tail(), "text/plain; charset=utf-8")
            elif path == "/api/status":
                self._send(json.dumps(status(conn), indent=1), "application/json")
            elif path == "/api/matrix":
                p = ROOT / "data" / "matrix.json"
                self._send(p.read_text() if p.exists() else "{}", "application/json")
            else:
                self._send("not found", code=404)
        finally:
            conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    print(f"admin: http://{a.host}:{a.port}")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
