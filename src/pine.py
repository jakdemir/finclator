"""Generate the TradingView Pine indicator from the DB → tradingview/finclator.pine

Pine can't fetch HTTP, so the signal history is embedded as run-length-encoded constants. The matrix changes at most
weekly, so 3 years × 9 cells is a few hundred numbers. Re-run after every pipeline run; paste into Pine editor.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from .db import connect
from .matrix import ASSETS, HORIZONS, build

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tradingview" / "finclator.pine"
LABEL_NUM = {"BUY": 1, "NEUTRAL": 0, "SELL": -1, "N/A": 0}


def history(conn: sqlite3.Connection, start: date, end: date, step_days: int = 7) -> dict[str, list[tuple[str, int]]]:
    """Weekly matrix snapshots from start→end, as (date, label) runs per cell."""
    series: dict[str, list[tuple[str, int]]] = {f"{a}:{h}": [] for a in ASSETS for h in HORIZONS}
    d = start
    while d <= end:
        m = build(conn, today=d, write=False)
        for k, cell in m["cells"].items():
            v = LABEL_NUM[cell["label"]]
            s = series[k]
            if not s or s[-1][1] != v:
                s.append((d.isoformat(), v))
        d += timedelta(days=step_days)
    return series


def _pine_array(runs: list[tuple[str, int]]) -> tuple[str, str]:
    ts = ", ".join(f"timestamp('{d} 00:00 +0000')" for d, _ in runs)
    vs = ", ".join(str(v) for _, v in runs)
    return f"array.from({ts})", f"array.from({vs})"


def render(series: dict[str, list[tuple[str, int]]], generated: str) -> str:
    decl = []
    for a in ASSETS:
        for h in HORIZONS:
            t, v = _pine_array(series[f"{a}:{h}"] or [("2020-01-01", 0)])
            decl.append(f"var {a.lower()}_{h.lower()}_t = {t}")
            decl.append(f"var {a.lower()}_{h.lower()}_v = {v}")
    decls = "\n".join(decl)
    return f'''// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © finclator — generated {generated}. Do not edit by hand; regenerate with `python -m src.pine`.
//@version=5
indicator("Finclator — influencer sentiment 3×3", shorttitle="Finclator", overlay=false, max_labels_count=50)

// ── embedded signal history (run-length: value applies from timestamp until the next one) ──────────────────
{decls}

f_at(tArr, vArr, t) =>
    v = 0
    for i = 0 to array.size(tArr) - 1
        if t >= array.get(tArr, i)
            v := array.get(vArr, i)
    v

// ── which asset is this chart? ──────────────────────────────────────────────────────────────────────────────
sym = syminfo.ticker
isBTC  = str.contains(sym, "BTC")
isGOLD = str.contains(sym, "XAU") or str.contains(sym, "GC") or str.contains(sym, "GOLD") or str.contains(sym, "GLD")
isSPX  = str.contains(sym, "SPX") or str.contains(sym, "SPY") or str.contains(sym, "ES") or str.contains(sym, "US500")

f_cell(asset, hz) =>
    asset == "BTC"  and hz == "S" ? f_at(btc_short_t,  btc_short_v,  time) :
    asset == "BTC"  and hz == "M" ? f_at(btc_medium_t, btc_medium_v, time) :
    asset == "BTC"  and hz == "L" ? f_at(btc_long_t,   btc_long_v,   time) :
    asset == "GOLD" and hz == "S" ? f_at(gold_short_t, gold_short_v, time) :
    asset == "GOLD" and hz == "M" ? f_at(gold_medium_t,gold_medium_v,time) :
    asset == "GOLD" and hz == "L" ? f_at(gold_long_t,  gold_long_v,  time) :
    asset == "SPX"  and hz == "S" ? f_at(spx_short_t,  spx_short_v,  time) :
    asset == "SPX"  and hz == "M" ? f_at(spx_medium_t, spx_medium_v, time) :
                                    f_at(spx_long_t,   spx_long_v,   time)

thisAsset = isBTC ? "BTC" : isGOLD ? "GOLD" : isSPX ? "SPX" : "BTC"
s = f_cell(thisAsset, "S")
m = f_cell(thisAsset, "M")
l = f_cell(thisAsset, "L")
wS = input.float(1.0, "weight SHORT",  minval=0, step=0.1)
wM = input.float(1.0, "weight MEDIUM", minval=0, step=0.1)
wL = input.float(1.0, "weight LONG",   minval=0, step=0.1)
composite = (s * wS + m * wM + l * wL) / (wS + wM + wL)

// ── plots (chart asset) ─────────────────────────────────────────────────────────────────────────────────────
cUp = color.new(#0a7d33, 0), cDn = color.new(#c0392b, 0), cFl = color.new(#8a8a8a, 0)
plot(composite, "composite", style=plot.style_columns, color=composite > 0.15 ? cUp : composite < -0.15 ? cDn : cFl)
plot(s, "SHORT",  color=color.new(#1a5fb4, 0), linewidth=1)
plot(m, "MEDIUM", color=color.new(#e08a00, 0), linewidth=1)
plot(l, "LONG",   color=color.new(#7b2cbf, 0), linewidth=2)
hline(0, color=color.new(color.gray, 60))
hline(1, color=color.new(color.gray, 85), linestyle=hline.style_dotted)
hline(-1, color=color.new(color.gray, 85), linestyle=hline.style_dotted)

// ── 3×3 table (all assets, current bar) ────────────────────────────────────────────────────────────────────
showTbl = input.bool(true, "show 3×3 table")
f_txt(v) => v > 0 ? "BUY" : v < 0 ? "SELL" : "NEUTRAL"
f_col(v) => v > 0 ? color.new(#0a7d33, 70) : v < 0 ? color.new(#c0392b, 70) : color.new(#8a8a8a, 80)
var tbl = table.new(position.top_right, 4, 4, border_width=1, border_color=color.new(color.gray, 70))
if showTbl and barstate.islast
    table.cell(tbl, 0, 0, "Finclator", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 0, "SHORT\\n0–3m",  text_color=color.gray, text_size=size.small)
    table.cell(tbl, 2, 0, "MEDIUM\\n3–12m", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 3, 0, "LONG\\n1–5y",   text_color=color.gray, text_size=size.small)
    assets = array.from("BTC", "GOLD", "SPX")
    for r = 0 to 2
        a = array.get(assets, r)
        table.cell(tbl, 0, r + 1, a, text_color=a == thisAsset ? color.white : color.gray, bgcolor=a == thisAsset ? color.new(color.blue, 60) : na, text_size=size.small)
        vS = f_cell(a, "S"), vM = f_cell(a, "M"), vL = f_cell(a, "L")
        table.cell(tbl, 1, r + 1, f_txt(vS), bgcolor=f_col(vS), text_color=color.white, text_size=size.small)
        table.cell(tbl, 2, r + 1, f_txt(vM), bgcolor=f_col(vM), text_color=color.white, text_size=size.small)
        table.cell(tbl, 3, r + 1, f_txt(vL), bgcolor=f_col(vL), text_color=color.white, text_size=size.small)
'''


if __name__ == "__main__":
    conn = connect()
    end = date.today()
    start = end - timedelta(days=3 * 365)
    ser = history(conn, start, end)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(ser, end.isoformat()))
    # also dump the JSON series for other consumers (dashboard, TV alternative transports)
    (ROOT / "data" / "matrix_history.json").write_text(json.dumps(ser, indent=1))

    print(OUT, {k: len(v) for k, v in ser.items()})
