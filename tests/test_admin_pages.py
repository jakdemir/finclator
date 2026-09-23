import json

from src import admin


def test_fixture_loads(conn):
    assert conn.execute("SELECT count(*) FROM tweets").fetchone()[0] == 4
    assert admin.status(conn)["calls"] == 2


def test_progress_account_rows_single_query(conn):
    rows = admin.account_rows(conn, "m")
    by = {r["handle"]: r for r in rows}
    assert by["alice"]["n"] == 2 and by["alice"]["rel"] == 2 and by["alice"]["cls"] == 2 and by["alice"]["calls"] == 1
    assert by["carol"]["n"] == 1 and by["carol"]["rel"] == 0 and by["carol"]["calls"] == 0
    assert by["alice"]["f"].startswith("2024-01-05") and by["alice"]["l"].startswith("2024-02-05")


def test_status_has_gate_counts_and_progress_marks_stale(conn):
    s = admin.status(conn)
    assert s["gated"] == 1 and s["gate_passed"] == 1 and s["gate_model"] == "jev-1.13.0"
    html = admin.page_progress(conn)
    assert "<small>Jev gate</small>" in html
    assert "class=stale" in html          # alice/bob last tweet years ago, active, → stale


def test_matrix_cells_link_to_audit(conn, tmp_path, monkeypatch):
    m = {"generated_at": "now", "model": "m",
         "cells": {"BTC:SHORT": {"label": "BUY", "n_calls": 3, "net": 0.4, "buy": 1, "sell": 0, "neutral": 0}}}
    monkeypatch.setattr(admin, "ROOT", tmp_path)          # ROOT/data/matrix.json
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "matrix.json").write_text(json.dumps(m))
    html = admin.page_matrix(conn)
    assert "href='/audit?asset=BTC&hz=SHORT'" in html


def test_accounts_ranking_folds_prior_only(conn):
    html = admin.page_accounts(conn)
    assert "<th title='Σ points" in html and ">points<" in html and ">hits<" not in html
    assert "<details><summary>2 accounts with no matured outcome" in html   # bob (call, no outcome) + carol
    assert html.index("@alice") < html.index("<details><summary>2 accounts")
