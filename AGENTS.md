# finclator — agent context

Finfluencer tweets → explicit, falsifiable market calls → evaluated against price when the horizon matures →
per-account trust → a 3×3 BUY/NEUTRAL/SELL matrix (BTC, GOLD, SPX × SHORT 0–3 mo / MEDIUM 3–12 mo / LONG 1–5 y)
plus `data/audit.html` and `tradingview/finclator.pine`. Spec: `specs/001-influencer-trust-scores/`. Branch
`001-influencer-trust-scores`. Standing product decisions live in the `social-sentiment-trading-signals` skill.

## Dev environment
- Python ≥3.11 (`/opt/homebrew/bin/python3`), venv at `.venv`; `.venv/bin/pip install -e ".[dev]"` (or `scripts/bootstrap.sh`, which also **wipes and rebuilds the DB** — don't run it casually).
- Run modules as `.venv/bin/python -m src.<mod>`; scripts as `PYTHONPATH=. .venv/bin/python scripts/<x>.py`.
- `.env` (gitignored): `TWITTERAPI_IO_KEY` (fetch), `ANTHROPIC_API_KEY` (API-mode classifier). Local classifier needs
  `FINCLATOR_MODEL_BASE_URL=http://localhost:11434/v1 FINCLATOR_MODEL=qwen3:30b-a3b-instruct-2507-q4_K_M` (Ollama).
- State is `data/finclator.db` (SQLite, WAL, **committed** to git); `-wal`/`-shm` and `*.log` are ignored.
- Admin UI: `FINCLATOR_ACTIVE_MODEL=<model> .venv/bin/python -m src.admin` → http://127.0.0.1:8787 (tabs: Progress,
  Matrix, Accounts, Audit, Architecture, Tables, `/api/status`). Run it in the background; verify with `urllib`, the
  browser tool blocks localhost.

## Commands
- Weekly pipeline: `.venv/bin/python -m src.run [--no-fetch] [--no-classify]` (fetch → classify → prices → evaluate → score → matrix → audit → pine).
- Backfill tweets: `PYTHONPATH=. .venv/bin/python scripts/backfill.py --workers 8` (resumable; verify with `pgrep -f backfill.py`).
- Classify backlog locally (resumable, newest→oldest, rebuilds trust/matrix/audit per batch):
  `FINCLATOR_MODEL_BASE_URL=... FINCLATOR_MODEL=... FINCLATOR_WORKERS=8 PYTHONPATH=. nohup .venv/bin/python scripts/classify_run.py`
  Stop with `pkill -f classify_run.py`. Nothing is ever re-classified (`classified_by(tweet_id, model)` PK).
- Model agreement vs frontier labels: `PYTHONPATH=. .venv/bin/python scripts/agreement.py [N] [data/labels_holdout.jsonl]`,
  then `scripts/agreement_diff.py {is_call|dir|hor}` to read disagreements.
- After changing `src/prefilter.py`: `PYTHONPATH=. .venv/bin/python scripts/reprefilter.py` (re-tags every stored tweet).
- Prefilter cases: `PYTHONPATH=. .venv/bin/python tests/test_prefilter.py` — a plain script printing `failures: N`;
  **`pytest` collects nothing** in this repo. Lint: `.venv/bin/ruff check .` (line length 110, rules E/F/W/I/B).
- Throughput bench: `PYTHONPATH=. .venv/bin/python scripts/bench_parallel.py 1 4 8`.

## Conventions (observed)
- Module per pipeline stage in `src/` (`fetch`, `prefilter`, `classify`, `prices`, `evaluate`, `score`, `matrix`, `audit`,
  `pine`, `admin`, `models`); each has `if __name__ == "__main__"` and takes a `conn` from `db.connect()`.
- Logging is `db.log(msg)` (UTC-timestamped, stdout + `data/pipeline.log`, tailed live by the admin page) — not bare `print`.
- Schema in `db.SCHEMA`, applied with `CREATE TABLE IF NOT EXISTS` on every `connect()`; additive migrations are
  `ALTER TABLE ADD COLUMN` guarded by `PRAGMA table_info`. Destructive migrations go in `scripts/migrate_*.py` with
  `PRAGMA foreign_keys=OFF` first.
- Model is a first-class dimension: `calls` unique per `(tweet_id, asset, model)`, `trust` keyed by model, published model
  = `models.active_model()` (`FINCLATOR_ACTIVE_MODEL` → `FINCLATOR_MODEL` → Fable backfill tag). Never sum across models.
- One classifier `SYSTEM` prompt in `src/classify.py` shared by every backend (Anthropic, Ollama native, OpenAI-compat).
  Ollama's `/v1` route silently drops `num_ctx`; the `:11434` branch uses `/api/chat` for that reason.
- Admin pages are f-string HTML built into a `B` list, `html.escape` as `e`, tables `class=sortable`, numeric headers get
  `title=` tooltips or a legend. Audit page is rendered inside the admin chrome via `admin._page`.
- Commit messages: one line, imperative, semicolon-separated scope list (see `git log --oneline`).

## Pitfalls
- Originals only: replies/RTs are rejected at the API call, the response filter, and the DB insert. `replies_in_db` / `rts_in_db` on Progress must stay 0.
- Horizons are 90/365/730 d maturity, defined once in `evaluate.MATURITY_DAYS`; do not add a second definition.
- Trust must be point-in-time (`score.compute(as_of=)`) for anything historical (Pine history, backtests).
- Python `\b` is ASCII-only — Turkish regex uses the explicit `_B0/_B1` boundaries in `prefilter.py`; `html.unescape` first.
- Nested f-strings with the same quote need Python 3.12; venv may be 3.11 → hoist to a local.
- `write_file` on an existing file is refused unless read in the same turn; `read_file` output is line-prefixed — never write it back.
- Prompt-tuning the classifier: score a **held-out** frontier-labeled set (`data/labels_holdout.jsonl`), not only the tuning set.
- Yahoo `query1.finance.yahoo.com/v8/finance/chart/<sym>` needs a browser UA; instruments are BTC-USD, `GC=F`, `^GSPC`.
