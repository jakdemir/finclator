"""matrix.build reports top_handle/top_share per cell and orders contributors by weight."""
from datetime import date

from src import db, matrix


def test_top_share(tmp_path):
    conn = db.connect_sqlite(tmp_path / "t.db")
    for h in ("big", "small"):
        conn.execute("INSERT INTO accounts(handle, school) VALUES(?, 'Macro')", (h,))
    # big: 3 BUY calls at conf 1.0 ; small: 1 BUY at conf 0.5 — no trust rows → 0.5 prior for both
    specs = [("big", 1.0)] * 3 + [("small", 0.5)]
    for i, (h, conf) in enumerate(specs):
        tid = f"{h}{i}"
        conn.execute("INSERT INTO tweets(id, handle, created_at, text, source) VALUES(?,?,?,?,?)",
                     (tid, h, "2026-09-20T00:00:00+00:00", "x", "csv"))
        conn.execute("INSERT INTO calls(tweet_id, handle, asset, direction, horizon, confidence, called_at, model) "
                     "VALUES(?,?,?,?,?,?,?,?)", (tid, h, "BTC", "BUY", "SHORT", conf, "2026-09-20T00:00:00+00:00", "m"))
    conn.commit()
    m = matrix.build(conn, today=date(2026, 9, 21), write=False, model="m")
    c = m["cells"]["BTC:SHORT"]
    assert c["top_handle"] == "big"
    assert abs(c["top_share"] - 1.5 / 1.75) < 1e-3
    assert c["contributors"][0]["handle"] == "big"
    assert c["contributors"][0]["weight"] >= c["contributors"][-1]["weight"]
    assert m["cells"]["GOLD:LONG"]["top_handle"] is None
