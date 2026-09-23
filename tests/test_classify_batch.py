"""classify_pending: batch routing on the Ollama path, and the Jev gate in front of the text model."""
from src import classify


class _Conn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def execute(self, *a, **k):
        raise AssertionError("no SQL expected in these tests")


def _rows(n):
    return [{"id": str(i), "handle": "h", "created_at": "2026-01-01T00:00:00+00:00", "text": "btc", "assets_hint": "BTC"}
            for i in range(n)]


def test_classify_pending_uses_batches(monkeypatch):
    rows = _rows(10)
    seen: list[int] = []

    def fake_batch():
        def run_batch(chunk):
            seen.append(len(chunk))
            return [{"is_call": False, "calls": []} for _ in chunk]
        return run_batch, "fake-model"

    def no_single():
        raise AssertionError("single path used")

    monkeypatch.setattr(classify, "GATE_ON", False)
    monkeypatch.setattr(classify, "MODEL", "fake-model")
    monkeypatch.setattr(classify, "BATCH_SIZE", 4)
    monkeypatch.setattr(classify, "BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(classify, "WORKERS", 2)
    monkeypatch.setattr(classify, "make_batch_classifier", fake_batch)
    monkeypatch.setattr(classify, "make_classifier", no_single)
    monkeypatch.setattr(classify, "pending", lambda conn, limit, model: rows)
    stored = []
    monkeypatch.setattr(classify, "store_result", lambda conn, t, r, m, g=None: stored.append((t["id"], m)) or 0)
    conn = _Conn()
    assert classify.classify_pending(conn) == (10, 0)
    assert sorted(seen) == [2, 4, 4]
    assert len(stored) == 10 and {m for _, m in stored} == {"fake-model"}
    assert conn.commits >= 1


def test_classify_pending_single_when_batch_size_1(monkeypatch):
    monkeypatch.setattr(classify, "GATE_ON", False)
    monkeypatch.setattr(classify, "BATCH_SIZE", 1)
    monkeypatch.setattr(classify, "BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(classify, "make_classifier", lambda: (lambda t: {"is_call": False, "calls": []}, "m"))
    monkeypatch.setattr(classify, "pending", lambda conn, limit, model: _rows(1))
    monkeypatch.setattr(classify, "store_result", lambda conn, t, r, m, g=None: 0)
    assert classify.classify_pending(_Conn()) == (1, 0)


def test_gate_blocks_and_reuses_before_text_model(monkeypatch):
    """10 pending: Jev blocks 6 (stored as non-calls, no GPU), 2 pass and reuse the plain model's label,
    2 pass and reach the text model. Everything is stored under the hybrid tag with gate_p attached."""
    from src import gate

    rows = _rows(10)
    gated = {t["id"]: {"model": "jev-1", "p_call": 0.9 if int(t["id"]) >= 6 else 0.1,
                       "stances": {"BTC": "up" if int(t["id"]) >= 6 else "none"}} for t in rows}
    monkeypatch.setattr(gate, "ensure", lambda conn, rs: gated)
    monkeypatch.setattr(classify, "GATE_ON", True)
    monkeypatch.setattr(classify, "GATE_REUSE", True)
    monkeypatch.setattr(classify, "MODEL", "text+jev")
    monkeypatch.setattr(classify, "BATCH_SIZE", 1)
    monkeypatch.setattr(classify, "BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(classify, "WORKERS", 1)
    monkeypatch.setattr(classify, "pending", lambda conn, limit, model: rows)
    old = {"6": [{"asset": "BTC", "direction": "BUY", "horizon": "SHORT", "confidence": 0.8, "price_target": None, "quote": "btc"}]}
    monkeypatch.setattr(classify, "_reusable", lambda conn, ids, base: (old, {"6", "7"}))
    text_seen = []

    def fake_single():
        def run(t):
            text_seen.append(t["id"])
            return {"is_call": True, "calls": [{"asset": "BTC", "direction": "SELL", "horizon": "LONG", "confidence": 0.7,
                                                "price_target": None, "quote": "btc"}]}
        return run, "text"
    monkeypatch.setattr(classify, "make_classifier", fake_single)
    stored = {}
    monkeypatch.setattr(classify, "store_result",
                        lambda conn, t, r, m, g=None: stored.__setitem__(t["id"], (m, r["is_call"], g)) or len(r["calls"]))
    assert classify.classify_pending(_Conn()) == (10, 3)
    assert sorted(text_seen) == ["8", "9"]
    assert {m for m, _, _ in stored.values()} == {"text+jev"}
    assert [stored[str(i)][1] for i in range(6)] == [False] * 6
    assert stored["6"] == ("text+jev", True, 0.9) and stored["7"] == ("text+jev", False, 0.9)
    assert stored["8"][1] and stored["9"][1]
    assert all(g is not None for _, _, g in stored.values())
