# finclator — agent context

Finfluencer tweets → explicit, falsifiable market calls → evaluated against price when the horizon matures →
per-account trust → a 3×3 BUY/NEUTRAL/SELL matrix (BTC, GOLD, SPX × SHORT 0–3 mo / MEDIUM 3–12 mo / LONG 1–5 y).
Surfaces: **finclator.com** (public landing + method page, gated admin panel), `data/audit.html`, and
`tradingview/finclator.pine` (publishing on hold). Spec: `specs/001-influencer-trust-scores/`. Branch `main`
(`001-influencer-trust-scores` kept in sync). Standing product decisions live in the
`social-sentiment-trading-signals` skill; site/panel/Vercel ops in its `references/website-ops.md`.

## State of play (2026-09-21)
- Backlog fully classified by `qwen3:30b-a3b-instruct-2507-q4_K_M` (49.7k tweets → 8.2k calls → 6.1k matured outcomes,
  67 accounts scored). Frontier labels (`claude-fable-5.1/interactive`, 297 + 120 holdout) coexist as a second model.
- **Database is Postgres (Neon, Vercel team Protocogni Labs)** via `DATABASE_URL` in `.env`; `data/finclator.db` is an
  untracked cold backup of the pre-migration state. `db.connect()` falls back to SQLite only when `DATABASE_URL` is unset.
- Site live at **https://finclator.com** (DNS at Cloudflare, cert issued, www → apex). Resend mail from
  `admin@finclator.com` verified end-to-end (sign-in links deliver). No open infra items.

## Dev environment
- Python ≥3.11 (venv is 3.14 at `.venv`); `.venv/bin/pip install -e ".[dev]"` (or `scripts/bootstrap.sh`, which also
  **wipes and rebuilds the DB** — don't run it casually).
- Run modules as `.venv/bin/python -m src.<mod>`; scripts as `PYTHONPATH=. .venv/bin/python scripts/<x>.py`.
- `.env` (gitignored): `DATABASE_URL` (Neon pooled), `TWITTERAPI_IO_KEY` (fetch), `ANTHROPIC_API_KEY` (API-mode
  classifier), `RESEND_API_KEY` + `MAIL_FROM` (mail). Local classifier needs
  `FINCLATOR_MODEL_BASE_URL=http://localhost:11434/v1 FINCLATOR_MODEL=qwen3:30b-a3b-instruct-2507-q4_K_M` (Ollama).
- Admin UI: `FINCLATOR_ACTIVE_MODEL=<model> .venv/bin/python -m src.admin` → http://127.0.0.1:8787 (tabs: Progress,
  Matrix, Accounts, Audit, Architecture, Tables, `/api/status`). Run it in the background; verify with `urllib`, the
  browser tool blocks localhost. Same pages are served hosted at finclator.com/panel by `api/panel.py`.
- Node deps (`package.json`, pnpm) exist only for `api/auth.js` (`@vercel/blob` ≥2, `resend`).

## Commands
- Weekly pipeline: `.venv/bin/python -m src.run [--no-fetch] [--no-classify]` (fetch → classify → prices → evaluate →
  score → matrix → audit → pine → site). Writes straight to Neon; the hosted panel reflects it without a deploy.
  `public/site.json` (landing numbers) still needs `vercel deploy --prod --yes` to go live.
- Deploy: `vercel deploy --prod --yes` (project linked to `protocogni/finclator`). Env: `vercel env ls`.
- Backfill tweets: `PYTHONPATH=. .venv/bin/python scripts/backfill.py --workers 8` (resumable; verify with `pgrep -f backfill.py`).
- Classify backlog locally (resumable, newest→oldest, rebuilds trust/matrix/audit per batch): `scripts/start_run.sh`
  (launchd jobs for Ollama + `scripts/classify_run.py` + admin; survive the desktop session) / `scripts/stop_run.sh`.
  Nothing is ever re-classified (`classified_by(tweet_id, model)` PK).
- Model agreement vs frontier labels: `PYTHONPATH=. .venv/bin/python scripts/agreement.py [N] [data/labels_holdout.jsonl]`,
  then `scripts/agreement_diff.py {is_call|dir|hor}` to read disagreements.
- After changing `src/prefilter.py`: `PYTHONPATH=. .venv/bin/python scripts/reprefilter.py` (re-tags every stored tweet).
- Prefilter cases: `PYTHONPATH=. .venv/bin/python tests/test_prefilter.py` — a plain script printing `failures: N`;
  **`pytest` collects nothing** in this repo. Lint: `.venv/bin/ruff check .` (line length 110, rules E/F/W/I/B;
  12 pre-existing warnings in scripts/ are known).
- SQLite → Postgres (re)migration: `DATABASE_URL=<unpooled> PYTHONPATH=. .venv/bin/python scripts/migrate_to_pg.py --yes`
  (truncates target, COPY, checksums, asserts identical matrix).

## Conventions (observed)
- Module per pipeline stage in `src/` (`fetch`, `prefilter`, `classify`, `prices`, `evaluate`, `score`, `matrix`, `audit`,
  `pine`, `site`, `admin`, `models`); each has `if __name__ == "__main__"` and takes a `conn` from `db.connect()`.
- **SQL is written in SQLite dialect everywhere**; `db._PgConnection.to_pg()` rewrites `?`, `INSERT OR IGNORE/REPLACE`,
  `datetime('now')`, `instr()` for Postgres. New idioms must be portable or added to `to_pg` — no `sum(<bool expr>)`,
  no `WHERE <int col>` without `=1`, no `PRAGMA`, no `sqlite_master` (use `db.tables/columns/primary_key`). Rows support
  `r["col"]`, `r[0]`, `.keys()` on both backends; Postgres `Decimal` arrives as `float`.
- Logging is `db.log(msg)` (UTC-timestamped, stdout + `data/pipeline.log`, tailed live by the admin page) — not bare `print`.
- Schema in `db.SCHEMA`; additive column migrations are entries in `db.MIGRATIONS` (applied on every `connect()` for
  both backends). Destructive migrations go in `scripts/migrate_*.py`.
- Model is a first-class dimension: `calls` unique per `(tweet_id, asset, model)`, `trust` keyed by model, published model
  = `models.active_model()` (`FINCLATOR_ACTIVE_MODEL` → `FINCLATOR_MODEL` → Fable backfill tag). Never sum across models.
- One classifier `SYSTEM` prompt in `src/classify.py` shared by every backend (Anthropic, Ollama native, OpenAI-compat).
  Ollama's `/v1` route silently drops `num_ctx`; the `:11434` branch uses `/api/chat` for that reason.
- Admin pages are f-string HTML built into a `B` list, `html.escape` as `e`, tables `class=sortable`, numeric headers get
  `title=` tooltips or a legend. Audit page is rendered inside the admin chrome via `admin._page`.
- Public pages: numbers only from `public/site.json`; no stack/model/infra names on `/` or `/method`.
- Commit messages: one line, imperative, semicolon-separated scope list (see `git log --oneline`).

## Pitfalls
- Originals only: replies/RTs are rejected at the API call, the response filter, and the DB insert. `replies_in_db` / `rts_in_db` on Progress must stay 0.
- Horizons are 90/365/730 d maturity, defined once in `evaluate.MATURITY_DAYS`; do not add a second definition.
- Trust must be point-in-time (`score.compute(as_of=)`) for anything historical (Pine history, backtests), and
  `matrix.build(today=)` must also bound `called_at` — without it the Pine history was flat BUY.
- Python `\b` is ASCII-only — Turkish regex uses the explicit `_B0/_B1` boundaries in `prefilter.py`; `html.unescape` first.
- `write_file` on an existing file is refused unless read in the same turn; `read_file` output is line-prefixed — never write it back.
- Prompt-tuning the classifier: score a **held-out** frontier-labeled set (`data/labels_holdout.jsonl`), not only the tuning set.
- Yahoo `query1.finance.yahoo.com/v8/finance/chart/<sym>` needs a browser UA; instruments are BTC-USD, `GC=F`, `^GSPC`.
- `node_modules/`, `.vercel/`, `.env.local`, `data/finclator.db` are gitignored — keep them so (the DB was 82 MB in git).
- `vercel env add` needs one env per call and no output redirection around it; `--sensitive` is refused on `development`.
