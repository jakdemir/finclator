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
    tabs = [("/", "Progress"), ("/matrix", "Matrix"), ("/accounts", "Accounts"), ("/audit", "Audit"), ("/api/status", "JSON")]
    nav = "".join(f"<a href='{h}' class='{'on' if h == active else ''}'>{t}</a>" for h, t in tabs)
    return (f"<!doctype html><meta charset=utf-8><title>Finclator admin — {title}</title>"
            f"<meta http-equiv=refresh content={60 if active == '/' else 30}><style>{CSS}</style><script>{JS}</script>"
            f"<nav>{nav}<span style='margin-left:auto;color:#9aa'>{datetime.now(timezone.utc):%H:%M:%S} UTC · {'page 60s · log live 3s' if active == '/' else 'auto-refresh 30s'}</span></nav>"
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
                          FROM accounts a LEFT JOIN trust t ON t.handle=a.handle AND t.asset='*' AND t.horizon='*'
                          GROUP BY a.school ORDER BY mean DESC"""):
        B.append(f"<tr><td>{e(r['school'] or '')}</td><td class=num>{r['n_acc']}</td><td class=num>{r['scored']}</td>"
                 f"<td class=num>{(r['mean'] or 0):.3f}</td><td class=num>{r['sn']}</td></tr>")
    B.append("</tbody></table>")
    return _page("matrix", "".join(B), "/matrix")


def page_accounts(conn) -> str:
    e = html.escape
    trust = {(r["handle"], r["asset"], r["horizon"]): r for r in _q(conn, "SELECT * FROM trust")}

    def tc(h, a, hz="*"):
        r = trust.get((h, a, hz))
        return f"<td class=num data-v={r['score'] if r else 0.5}>{r['score']:.2f}<small> n={r['n']}</small></td>" if r else "<td class=num data-v=0.5><small>–</small></td>"

    B = ["<h2>Trust scores <small>(shrunk toward 0.5; n = matured outcomes)</small></h2>",
         "<table class=sortable><thead><tr><th>account</th><th>school</th><th>calls</th><th>n</th><th>hits</th><th>overall</th>",
         "<th>BTC</th><th>GOLD</th><th>SPX</th><th>SHORT</th><th>MEDIUM</th><th>LONG</th></tr></thead><tbody>"]
    for r in _q(conn, """SELECT a.handle, a.school, (SELECT count(*) FROM calls c WHERE c.handle=a.handle) calls FROM accounts a"""):
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
