"""Build a self-contained HTML audit page: every call with tweet link, quote, label, horizon, and (when matured)
entry/exit prices with links to verify them on TradingView / Yahoo.  Output: data/audit.html
"""
from __future__ import annotations

import html
import json
from datetime import date, timedelta
from pathlib import Path

from .db import connect
from .evaluate import MATURITY_DAYS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "audit.html"

TV = {"BTC": "BITSTAMP:BTCUSD", "GOLD": "COMEX:GC1!", "SPX": "SP:SPX"}
YH = {"BTC": "BTC-USD", "GOLD": "GC=F", "SPX": "%5EGSPC"}
HZ = {"SHORT": "0–3 mo (eval 90d)", "MEDIUM": "3–12 mo (eval 365d)", "LONG": "1–5 y (eval 730d)"}


def _yahoo_hist(asset: str, d: str) -> str:
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
    p1 = int(dt.timestamp()) - 5 * 86400
    p2 = int(dt.timestamp()) + 5 * 86400
    return f"https://finance.yahoo.com/quote/{YH[asset]}/history/?period1={p1}&period2={p2}"


def _tv(asset: str) -> str:
    return f"https://www.tradingview.com/chart/?symbol={TV[asset]}"


def _hl(text: str, quote: str | None) -> str:
    t = html.escape(text)
    if quote and quote in text:
        q = html.escape(quote)
        t = t.replace(q, f"<mark>{q}</mark>", 1)
    return t.replace("\n", "<br>")


def build() -> Path:
    conn = connect()
    rows = conn.execute("""
        SELECT c.id, c.handle, c.asset, c.direction, c.horizon, c.confidence, c.quote, c.called_at, c.tweet_id,
               t.text, o.entry_date, o.exit_date, o.entry_close, o.exit_close, o.return_pct, o.threshold_pct,
               o.actual, o.result
        FROM calls c JOIN tweets t ON t.id = c.tweet_id LEFT JOIN outcomes o ON o.call_id = c.id
        ORDER BY c.handle, c.called_at DESC""").fetchall()
    trust = {(r["handle"], r["asset"], r["horizon"]): r for r in conn.execute("SELECT * FROM trust")}
    matrix = json.loads((ROOT / "data" / "matrix.json").read_text())

    parts = [f"""<!doctype html><meta charset=utf-8><title>Finclator audit</title>
<style>
body{{font:14px/1.4 -apple-system,system-ui,sans-serif;margin:24px;color:#222}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:6px 8px;vertical-align:top}}
th{{background:#f4f4f4;position:sticky;top:0}} mark{{background:#ffe58a}}
.BUY{{color:#0a7d33;font-weight:600}} .SELL{{color:#c0392b;font-weight:600}} .NEUTRAL{{color:#666;font-weight:600}}
.CORRECT{{background:#e6f6ea}} .WRONG{{background:#fbe9e7}} .PARTIAL{{background:#fff8e1}}
.tweet{{max-width:520px;font-size:13px}} .num{{text-align:right;white-space:nowrap}} small{{color:#777}}
.grid td{{text-align:center;font-size:18px;width:120px}}
</style>
<h1>Finclator audit — {len(rows)} calls</h1>
<p>Each row is one (tweet, asset) call. <b>Verify:</b> open the tweet link → read the highlighted quote → check the
label/horizon; open the Yahoo link (±5 days around the date) or the TradingView chart → check entry/exit closes.
Prices: BTC = Yahoo BTC-USD (daily UTC close), GOLD = COMEX front-month <code>GC=F</code>, SPX = <code>^GSPC</code>.
NEUTRAL band = 0.5σ·√days of trailing-1y daily vol at entry, shown as ±thr%.</p>
<h2>Matrix (as of {matrix['generated_at'][:10]})</h2><table class=grid><tr><th></th><th>SHORT</th><th>MEDIUM</th><th>LONG</th></tr>"""]
    for a in ("BTC", "GOLD", "SPX"):
        cells = "".join(f"<td class={matrix['cells'][f'{a}:{h}']['label']}>{matrix['cells'][f'{a}:{h}']['label']}"
                        f"<br><small>n={matrix['cells'][f'{a}:{h}']['n_calls']} net={matrix['cells'][f'{a}:{h}']['net']}</small></td>"
                        for h in ("SHORT", "MEDIUM", "LONG"))
        parts.append(f"<tr><th>{a}</th>{cells}</tr>")
    parts.append("</table>")

    parts.append("<h2>Trust scores</h2><table><tr><th>account</th><th>asset</th><th>horizon</th><th>n</th><th>hits</th><th>score</th></tr>")
    for k in sorted(trust):
        r = trust[k]
        parts.append(f"<tr><td>{r['handle']}</td><td>{r['asset']}</td><td>{r['horizon']}</td><td class=num>{r['n']}</td>"
                     f"<td class=num>{r['correct']:.1f}</td><td class=num>{r['score']:.3f}</td></tr>")
    parts.append("</table>")

    parts.append("""<h2>Calls</h2><table><tr><th>#</th><th>account / date</th><th class=tweet>tweet (quote highlighted)</th>
<th>asset</th><th>call</th><th>horizon</th><th>conf</th><th>entry</th><th>exit</th><th>return</th><th>market did</th><th>result</th><th>verify</th></tr>""")
    for r in rows:
        d = r["called_at"][:10]
        link = f"https://x.com/{r['handle']}/status/{r['tweet_id']}"
        if r["result"]:
            entry = f"{r['entry_date']}<br>{r['entry_close']:,.2f}"
            exit_ = f"{r['exit_date']}<br>{r['exit_close']:,.2f}"
            ret = f"{r['return_pct']:+.1f}%<br><small>±{r['threshold_pct']:.1f}%</small>"
            actual, result = r["actual"], r["result"]
            verify = (f"<a href='{_yahoo_hist(r['asset'], r['entry_date'])}'>entry</a> · "
                      f"<a href='{_yahoo_hist(r['asset'], r['exit_date'])}'>exit</a> · <a href='{_tv(r['asset'])}'>TV</a>")
        else:
            mat = date.fromisoformat(d) + timedelta(days=MATURITY_DAYS[r["horizon"]])
            entry = exit_ = ret = actual = ""
            result = f"<small>matures {mat}</small>"
            verify = f"<a href='{_tv(r['asset'])}'>TV</a>"
        parts.append(f"""<tr class={r['result'] or ''}><td>{r['id']}</td><td>@{r['handle']}<br><small>{d}</small><br><a href='{link}'>tweet ↗</a></td>
<td class=tweet>{_hl(r['text'], r['quote'])}</td><td>{r['asset']}</td><td class={r['direction']}>{r['direction']}</td>
<td>{r['horizon']}<br><small>{HZ[r['horizon']]}</small></td><td class=num>{r['confidence']:.2f}</td>
<td class=num>{entry}</td><td class=num>{exit_}</td><td class=num>{ret}</td><td class={actual}>{actual}</td><td>{result}</td><td>{verify}</td></tr>""")
    parts.append("</table>")
    OUT.write_text("\n".join(parts))
    return OUT


if __name__ == "__main__":
    print(build())
