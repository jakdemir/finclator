"""Verification & debugging page → data/audit.html (self-contained, no server).

Sections: matrix · pipeline funnel · accounts (trust, volume, sampling) · calls (filterable, with tweet link,
highlighted quote, entry/exit prices, target hit, Yahoo/TradingView verify links) · prefilter rejects sample ·
price coverage.
"""
from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .db import connect
from .evaluate import MATURITY_DAYS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "audit.html"

TV = {"BTC": "BITSTAMP:BTCUSD", "GOLD": "COMEX:GC1!", "SPX": "SP:SPX"}
YH = {"BTC": "BTC-USD", "GOLD": "GC=F", "SPX": "%5EGSPC"}
HZ = {"SHORT": "0–3 mo · eval 90d", "MEDIUM": "3–12 mo · eval 365d", "LONG": "1–5 y · eval 730d"}

CSS = """
body{font:13px/1.45 -apple-system,system-ui,sans-serif;margin:0;padding:20px 24px;color:#1b1b1b;background:#fff}
h1{margin:0 0 4px}h2{margin:28px 0 8px;font-size:17px;border-bottom:1px solid #ddd;padding-bottom:4px}
table{border-collapse:collapse;width:100%}th,td{border:1px solid #e3e3e3;padding:5px 7px;vertical-align:top;text-align:left}
th{background:#f5f5f5;position:sticky;top:0;z-index:1;cursor:pointer}th:hover{background:#e9e9e9}
mark{background:#ffe58a;padding:0 1px}small{color:#777}.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.BUY{color:#0a7d33;font-weight:600}.SELL{color:#c0392b;font-weight:600}.NEUTRAL{color:#666;font-weight:600}.NA{color:#aaa}
tr.CORRECT td{background:#eefaf1}tr.WRONG td{background:#fdeeec}tr.PARTIAL td{background:#fff9e3}
.tweet{max-width:560px;white-space:pre-wrap}.grid td{text-align:center;font-size:18px;width:130px;padding:10px}
.hit1{color:#0a7d33}.hit0{color:#c0392b}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px;align-items:center}
select,input{font:inherit;padding:3px 6px}.pill{background:#eee;border-radius:10px;padding:1px 8px;font-size:12px}
a{color:#1a5fb4;text-decoration:none}a:hover{text-decoration:underline}.hidden{display:none}
details summary{cursor:pointer;color:#1a5fb4}
"""

JS = """
function filt(){const a=v('f-acc'),s=v('f-asset'),h=v('f-hz'),r=v('f-res'),d=v('f-dir'),q=v('f-q').toLowerCase();
let n=0;document.querySelectorAll('#calls tbody tr').forEach(tr=>{const D=tr.dataset;
const ok=(!a||D.acc===a)&&(!s||D.asset===s)&&(!h||D.hz===h)&&(!r||D.res===r)&&(!d||D.dir===d)&&(!q||tr.textContent.toLowerCase().includes(q));
tr.classList.toggle('hidden',!ok);if(ok)n++;});document.getElementById('f-n').textContent=n+' shown';}
function v(id){return document.getElementById(id).value}
function sortTable(tbl,col){const tb=tbl.tBodies[0],rows=[...tb.rows],asc=tbl.dataset.sc!=col+'a';
rows.sort((x,y)=>{const a=x.cells[col].dataset.v??x.cells[col].textContent,b=y.cells[col].dataset.v??y.cells[col].textContent;
const na=parseFloat(a),nb=parseFloat(b);const c=(!isNaN(na)&&!isNaN(nb))?na-nb:a.localeCompare(b);return asc?c:-c;});
rows.forEach(r=>tb.appendChild(r));tbl.dataset.sc=col+(asc?'a':'d');}
document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('table.sortable th').forEach((th,i)=>th.onclick=()=>sortTable(th.closest('table'),i));
['f-acc','f-asset','f-hz','f-res','f-dir'].forEach(id=>document.getElementById(id).onchange=filt);document.getElementById('f-q').oninput=filt;filt();});
"""


def _yahoo(asset: str, d: str) -> str:
    ts = int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp())
    return f"https://finance.yahoo.com/quote/{YH[asset]}/history/?period1={ts - 5 * 86400}&period2={ts + 5 * 86400}"


def _tv(asset: str) -> str:
    return f"https://www.tradingview.com/chart/?symbol={TV[asset]}"


def _hl(text: str, quote: str | None) -> str:
    t = html.escape(text)
    if quote and quote in text:
        q = html.escape(quote)
        t = t.replace(q, f"<mark>{q}</mark>", 1)
    return t


def _fmt(x, nd=2):
    return "" if x is None else f"{x:,.{nd}f}"


def build() -> Path:
    conn = connect()
    e = html.escape
    now = datetime.now(timezone.utc)
    matrix_p = ROOT / "data" / "matrix.json"
    matrix = json.loads(matrix_p.read_text()) if matrix_p.exists() else {"generated_at": "", "cells": {}}

    P = [f"<!doctype html><meta charset=utf-8><title>Finclator — verification</title><style>{CSS}</style><script>{JS}</script>"]
    P.append(f"<h1>Finclator verification &amp; debug</h1><small>generated {now:%Y-%m-%d %H:%M} UTC · "
             "prices: BTC=Yahoo BTC-USD (UTC close), GOLD=COMEX GC=F front month, SPX=^GSPC · "
             "flat band = 0.5σ·√days (trailing-1y daily vol at entry)</small>")

    # ---- matrix
    P.append("<h2>Matrix</h2><table class=grid><tr><th></th><th>SHORT<br><small>0–3 mo</small></th><th>MEDIUM<br><small>3–12 mo</small></th><th>LONG<br><small>1–5 y</small></th></tr>")
    for a in ("BTC", "GOLD", "SPX"):
        tds = ""
        for h in ("SHORT", "MEDIUM", "LONG"):
            c = matrix["cells"].get(f"{a}:{h}", {"label": "N/A", "n_calls": 0, "net": 0})
            cls = c["label"] if c["label"] != "N/A" else "NA"
            tds += f"<td class={cls}>{c['label']}<br><small>n={c['n_calls']} net={c['net']:+.2f}</small></td>"
        P.append(f"<tr><th>{a}</th>{tds}</tr>")
    P.append("</table>")

    # ---- funnel
    f = conn.execute("""SELECT count(*) t, sum(relevant) rel, sum(relevant AND classified) cls,
                        (SELECT count(*) FROM calls) calls, (SELECT count(*) FROM outcomes) outs,
                        (SELECT count(DISTINCT tweet_id) FROM calls) call_tweets FROM tweets""").fetchone()
    P.append(f"""<h2>Pipeline funnel</h2><div class=bar>
<span class=pill>tweets stored: <b>{f['t']:,}</b></span> →
<span class=pill>asset-mentioning (prefilter): <b>{f['rel']:,}</b></span> →
<span class=pill>classified: <b>{f['cls']:,}</b></span> →
<span class=pill>tweets with calls: <b>{f['call_tweets']:,}</b> ({f['calls']:,} calls)</span> →
<span class=pill>matured &amp; evaluated: <b>{f['outs']:,}</b></span></div>""")
    pend = f["rel"] - f["cls"]
    if pend:
        P.append(f"<p><b>{pend:,}</b> tweets await classification.</p>")

    # ---- accounts
    P.append("<h2>Accounts</h2><table class=sortable><thead><tr><th>account</th><th>school</th><th>lang</th>"
             "<th>followers</th><th>orig/yr</th><th>sampling</th><th>tweets</th><th>relevant</th><th>calls</th>"
             "<th>evaluated</th><th>hits</th><th>trust</th><th>BTC</th><th>GOLD</th><th>SPX</th><th>first</th><th>last</th></tr></thead><tbody>")
    acc = conn.execute("""
        SELECT a.handle, a.school, a.language, a.followers, a.rate_per_year, a.sampling, a.active,
               (SELECT count(*) FROM tweets t WHERE t.handle=a.handle) n_t,
               (SELECT sum(relevant) FROM tweets t WHERE t.handle=a.handle) n_rel,
               (SELECT count(*) FROM calls c WHERE c.handle=a.handle) n_c,
               (SELECT min(created_at) FROM tweets t WHERE t.handle=a.handle) first_t,
               (SELECT max(created_at) FROM tweets t WHERE t.handle=a.handle) last_t
        FROM accounts a ORDER BY a.handle""").fetchall()
    trust = {(r["handle"], r["asset"], r["horizon"]): r for r in conn.execute("SELECT * FROM trust")}

    def tcell(h, a):
        r = trust.get((h, a, "*"))
        return f"<td class=num data-v='{r['score'] if r else 0}'>{r['score']:.2f}<br><small>n={r['n']}</small></td>" if r else "<td class=num data-v=0><small>–</small></td>"

    for r in acc:
        ov = trust.get((r["handle"], "*", "*"))
        P.append(f"<tr><td><a href='https://x.com/{r['handle']}'>@{e(r['handle'])}</a>{'' if r['active'] else ' <small>(inactive)</small>'}</td>"
                 f"<td>{e(r['school'] or '')}</td><td>{r['language']}</td>"
                 f"<td class=num>{_fmt(r['followers'], 0)}</td><td class=num>{_fmt(r['rate_per_year'], 0)}</td>"
                 f"<td>{e(r['sampling'] or 'full')}</td><td class=num>{r['n_t'] or 0}</td><td class=num>{r['n_rel'] or 0}</td>"
                 f"<td class=num>{r['n_c']}</td>")
        if ov:
            P.append(f"<td class=num>{ov['n']}</td><td class=num>{_fmt(ov['correct'], 1)}</td>"
                     f"<td class=num data-v='{ov['score']}'><b>{ov['score']:.3f}</b></td>")
        else:
            P.append("<td class=num>0</td><td></td><td class=num data-v=0.5><small>0.500 (prior)</small></td>")
        P.append(tcell(r["handle"], "BTC") + tcell(r["handle"], "GOLD") + tcell(r["handle"], "SPX"))
        P.append(f"<td><small>{(r['first_t'] or '')[:10]}</small></td><td><small>{(r['last_t'] or '')[:10]}</small></td></tr>")
    P.append("</tbody></table>")

    # ---- calls
    rows = conn.execute("""
        SELECT c.id, c.handle, c.asset, c.direction, c.horizon, c.confidence, c.price_target, c.quote, c.called_at,
               c.tweet_id, c.model, t.text, o.entry_date, o.exit_date, o.entry_close, o.exit_close, o.return_pct,
               o.threshold_pct, o.actual, o.result, o.target_hit, o.extreme
        FROM calls c JOIN tweets t ON t.id = c.tweet_id LEFT JOIN outcomes o ON o.call_id = c.id
        ORDER BY c.called_at DESC""").fetchall()
    handles = sorted({r["handle"] for r in rows})
    P.append(f"""<h2>Calls ({len(rows)})</h2><div class=bar>
<select id=f-acc><option value="">all accounts</option>{''.join(f'<option>{e(h)}</option>' for h in handles)}</select>
<select id=f-asset><option value="">all assets</option><option>BTC</option><option>GOLD</option><option>SPX</option></select>
<select id=f-hz><option value="">all horizons</option><option>SHORT</option><option>MEDIUM</option><option>LONG</option></select>
<select id=f-dir><option value="">all directions</option><option>BUY</option><option>SELL</option><option>NEUTRAL</option></select>
<select id=f-res><option value="">all results</option><option>CORRECT</option><option>PARTIAL</option><option>WRONG</option><option value=PENDING>pending</option></select>
<input id=f-q placeholder="search text…" size=28> <span id=f-n class=pill></span></div>
<p><b>How to verify a row:</b> open <i>tweet ↗</i>, read the highlighted quote, judge asset / direction / horizon / target.
Then open <i>entry</i> / <i>exit</i> (Yahoo history, ±5 days) or <i>TV</i> and compare the closes. <i>market did</i> is the realised direction
vs the flat band; <i>target</i> shows whether the stated level was touched by any close inside the horizon (extreme = best close reached).</p>
<table id=calls class=sortable><thead><tr><th>#</th><th>account · date</th><th class=tweet>tweet (quote highlighted)</th><th>asset</th>
<th>call</th><th>horizon</th><th>conf</th><th>target</th><th>entry</th><th>exit</th><th>return</th><th>market did</th><th>result</th><th>verify</th></tr></thead><tbody>""")
    for r in rows:
        d = r["called_at"][:10]
        res = r["result"] or "PENDING"
        if r["result"]:
            entry = f"{r['entry_date']}<br>{_fmt(r['entry_close'])}"
            exit_ = f"{r['exit_date']}<br>{_fmt(r['exit_close'])}"
            ret = f"{r['return_pct']:+.1f}%<br><small>flat ±{r['threshold_pct']:.1f}%</small>"
            actual = f"<span class={r['actual']}>{r['actual']}</span>"
            result = r["result"]
            verify = (f"<a href='{_yahoo(r['asset'], r['entry_date'])}'>entry</a> · <a href='{_yahoo(r['asset'], r['exit_date'])}'>exit</a>"
                      f" · <a href='{_tv(r['asset'])}'>TV</a>")
        else:
            mat = date.fromisoformat(d) + timedelta(days=MATURITY_DAYS[r["horizon"]])
            entry = exit_ = ret = actual = ""
            result = f"<small>matures {mat}</small>"
            verify = f"<a href='{_tv(r['asset'])}'>TV</a>"
        if r["price_target"]:
            tgt = _fmt(r["price_target"], 0)
            if r["target_hit"] is not None:
                tgt += f"<br><small class=hit{r['target_hit']}>{'HIT' if r['target_hit'] else 'miss'} · ext {_fmt(r['extreme'], 0)}</small>"
        else:
            tgt = "<small>–</small>"
        P.append(f"""<tr class="{r['result'] or ''}" data-acc="{e(r['handle'])}" data-asset="{r['asset']}" data-hz="{r['horizon']}" data-res="{res}" data-dir="{r['direction']}">
<td data-v={r['id']}>{r['id']}</td><td>@{e(r['handle'])}<br><small>{d}</small><br><a href='https://x.com/{r['handle']}/status/{r['tweet_id']}'>tweet ↗</a></td>
<td class=tweet>{_hl(r['text'], r['quote'])}</td><td>{r['asset']}</td><td class={r['direction']}>{r['direction']}</td>
<td>{r['horizon']}<br><small>{HZ[r['horizon']]}</small></td><td class=num>{r['confidence']:.2f}</td><td class=num>{tgt}</td>
<td class=num>{entry}</td><td class=num>{exit_}</td><td class=num data-v='{r['return_pct'] or 0}'>{ret}</td><td>{actual}</td><td>{result}</td><td>{verify}</td></tr>""")
    P.append("</tbody></table>")

    # ---- debug: rejects + classified non-calls
    P.append("<h2>Debug</h2>")
    rej = conn.execute("""SELECT handle, created_at, text, assets_hint FROM tweets WHERE relevant=1 AND classified=1
                          AND id NOT IN (SELECT tweet_id FROM calls) ORDER BY random() LIMIT 30""").fetchall()
    P.append("<details><summary>Sample of asset-mentioning tweets the classifier judged <b>not a call</b> (30 random) — check for missed calls</summary><table>")
    for r in rej:
        P.append(f"<tr><td>@{e(r['handle'])}<br><small>{r['created_at'][:10]} · {r['assets_hint']}</small></td><td class=tweet>{e(r['text'])}</td></tr>")
    P.append("</table></details>")
    norel = conn.execute("""SELECT handle, created_at, text FROM tweets WHERE relevant=0 AND is_reply=0
                            ORDER BY random() LIMIT 30""").fetchall()
    P.append("<details><summary>Sample of tweets the <b>prefilter dropped</b> (no asset keyword; 30 random) — check for missed asset mentions</summary><table>")
    for r in norel:
        P.append(f"<tr><td>@{e(r['handle'])}<br><small>{r['created_at'][:10]}</small></td><td class=tweet>{e(r['text'])}</td></tr>")
    P.append("</table></details>")
    P.append("<details><summary>Price coverage</summary><table><tr><th>asset</th><th>from</th><th>to</th><th>rows</th><th>last close</th></tr>")
    for r in conn.execute("SELECT asset, min(date) a, max(date) b, count(*) n FROM prices GROUP BY asset"):
        last = conn.execute("SELECT close FROM prices WHERE asset=? ORDER BY date DESC LIMIT 1", (r["asset"],)).fetchone()[0]
        P.append(f"<tr><td>{r['asset']}</td><td>{r['a']}</td><td>{r['b']}</td><td class=num>{r['n']}</td><td class=num>{_fmt(last)}</td></tr>")
    P.append("</table></details>")
    P.append("<details><summary>Scoring rules</summary><ul>"
             "<li>Direction: CORRECT=1, PARTIAL (off by one step, e.g. BUY vs flat)=0.5, WRONG=0.</li>"
             "<li>Price target: +0.25 if touched within horizon, −0.25 if not (clamped 0–1).</li>"
             "<li>Trust = (Σhits + 5) / (n + 10): shrinkage toward 0.5; n≈10 before the score means much.</li>"
             "<li>Matrix weight per call = trust(account, asset, horizon → fallbacks) × confidence × 2^(−age / (window/3)); hard cutoff at window.</li>"
             "<li>Cell label: net=(buy−sell)/total; BUY &gt; +0.15, SELL &lt; −0.15, else NEUTRAL; N/A when total weight &lt; 0.3.</li></ul></details>")
    OUT.write_text("\n".join(P))
    return OUT


def render() -> str:
    """Build and return the HTML (also refreshes data/audit.html)."""
    return build().read_text()


if __name__ == "__main__":
    print(build())
