"""classify_pending must route through make_batch_classifier when BATCH_SIZE > 1 on the Ollama path."""
from src import classify


class _Conn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


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

    monkeypatch.setattr(classify, "BATCH_SIZE", 4)
    monkeypatch.setattr(classify, "BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(classify, "WORKERS", 2)
    monkeypatch.setattr(classify, "make_batch_classifier", fake_batch)
    monkeypatch.setattr(classify, "make_classifier", no_single)
    monkeypatch.setattr(classify, "pending", lambda conn, limit, model: rows)
    stored = []
    monkeypatch.setattr(classify, "store_result", lambda conn, t, r, m: stored.append((t["id"], m)) or 0)
    conn = _Conn()
    assert classify.classify_pending(conn) == (10, 0)
    assert sorted(seen) == [2, 4, 4]
    assert len(stored) == 10 and {m for _, m in stored} == {"fake-model"}
    assert conn.commits >= 1


def test_classify_pending_single_when_batch_size_1(monkeypatch):
    monkeypatch.setattr(classify, "BATCH_SIZE", 1)
    monkeypatch.setattr(classify, "BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(classify, "make_classifier", lambda: (lambda t: {"is_call": False, "calls": []}, "m"))
    monkeypatch.setattr(classify, "pending", lambda conn, limit, model: _rows(1))
    monkeypatch.setattr(classify, "store_result", lambda conn, t, r, m: 0)
    assert classify.classify_pending(_Conn()) == (1, 0)
