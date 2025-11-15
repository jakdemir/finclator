# Implementation Plan: Finclator Influencer Trust-Scoring MVP

**Branch**: `001-influencer-trust-scores` | **Date**: 2025-11-15 | **Spec**: `specs/001-influencer-trust-scores/spec.md`  
**Input**: Feature specification from `specs/001-influencer-trust-scores/spec.md` and user technical plan description

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Finclator ingests influencer tweets and market price data to generate calibrated Buy / Neutral / Sell indicators for BTC, Gold, and the S&P 500 across short-, medium-, and long-term horizons.  
The MVP will be implemented as a small Python backend consisting of a FastAPI read-only API and a worker service, both running on Render against a single PostgreSQL database, plus scheduled jobs for tweet ingestion, sentiment classification, price ingestion, outcome evaluation, and signal aggregation.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, SQLAlchemy + asyncpg (or equivalent async DB client), HTTPX/requests, OpenAI-compatible client for grok-3-fast and grok-3-mini, Pydantic  
**Storage**: Render-managed PostgreSQL (single primary database for all entities)  
**Testing**: pytest, HTTPX-based API tests, factory-style fixtures for DB entities  
**Target Platform**: Render web service (FastAPI), Render background worker, Render Cron Jobs (Linux containers)  
**Project Type**: Single backend project (API + worker processes from shared codebase, no frontend)  
**Performance Goals**:  
- P95 latency \< 500ms for read-only indicator endpoints under expected early usage  
- Ingestion, evaluation, and aggregation jobs keep indicators no more than 5–10 minutes behind live data  
**Constraints**:  
- No user accounts, dashboards, or complex UI in MVP (JSON/CLI-style outputs only)  
- Respect X and Alpha Vantage rate limits and terms of service  
- Minimize external dependencies beyond X API, Alpha Vantage, and grok models  
**Scale/Scope**:  
- Initial scope limited to a fixed list of influencers (dozens, not thousands) and three assets (BTC, GOLD, SPX)  
- Pipeline optimized for daily tweet volumes in the hundreds, with room to scale later

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

From the Finclator Constitution:

1. **Simplicity & Focus**  
   - **Rule**: The MVP MUST focus only on core prediction logic and data acquisition. Non-essential features (e.g., user accounts, complex UI/UX) are deferred.  
   - **Plan Alignment**:  
     - Only a FastAPI read API, worker scripts, and scheduled jobs are implemented—no authentication, dashboards, or multi-screen UX.  
     - All code is oriented around ingestion, sentiment extraction, trust scoring, and signal aggregation; no secondary product features are included.

2. **Data-Driven Trust**  
   - **Rule**: The trust score methodology MUST be transparent, auditable, and directly linked to influencer sentiment and historical market performance.  
   - **Plan Alignment**:  
     - Database schema includes explicit tables for sentiments, price history, outcomes, and trust scores, allowing back-tracing from any indicator to underlying data.  
     - Evaluation scripts compute CORRECT/WRONG/UNCLEAR outcomes based on price windows, feeding directly into trust-score calculations used for weighting signals.  
     - API exposes school-level and influencer-level breakdowns so users can see how scores are derived.

**Gate Evaluation (pre-design)**: PASS  
- The proposed architecture uses a minimal set of services and focuses exclusively on data ingestion, calibration, and read-only exposure of indicators and explanations.  
- Trust is grounded in measurable outcomes (prediction vs. realized price moves) with persisted audit trails in PostgreSQL.

## Project Structure

### Documentation (this feature)

```text
specs/001-influencer-trust-scores/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (tech decisions and tradeoffs)
├── data-model.md        # Phase 1 output (entities and relationships)
├── quickstart.md        # Phase 1 output (end-to-end test flows)
├── contracts/           # Phase 1 output (API contracts, e.g., OpenAPI)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── routers/
│   │   ├── signals.py           # /signals, /school-signals endpoints
│   │   └── influencers.py       # /influencers/{id} endpoint(s)
│   └── dependencies.py          # DB sessions, common deps
├── workers/
│   ├── tweet_ingestion.py       # Scheduled: fetch influencer tweets and insert unprocessed rows
│   ├── sentiment.py             # Scheduled: classify unprocessed tweets via grok models
│   ├── price_ingestion.py       # Scheduled: fetch OHLCV from Alpha Vantage
│   ├── evaluation.py            # Scheduled: compute CORRECT/WRONG/UNCLEAR outcomes
│   └── aggregation.py           # Scheduled: compute current trust scores and signals
├── db/
│   ├── models.py                # SQLAlchemy models aligned with data-model.md
│   ├── schema.py                # Pydantic schemas for API I/O
│   └── session.py               # Engine, session/connection management
└── services/
    ├── sentiment_classifier.py  # Thin wrapper around grok-3-fast/grok-3-mini
    ├── price_provider.py        # Alpha Vantage integration
    ├── trust_scoring.py         # Trust score update logic from outcomes
    └── signal_aggregator.py     # Aggregation into school-level and final signals

tests/
├── contract/
│   └── test_api_contracts.py    # Shape and semantics of public endpoints
├── integration/
│   ├── test_end_to_end_pipeline.py  # Ingestion → sentiment → evaluation → aggregation
│   └── test_signals_api.py          # API over real-ish DB state
└── unit/
    ├── test_trust_scoring.py
    ├── test_signal_aggregator.py
    └── test_sentiment_classifier.py
```

**Structure Decision**:  
- Single backend project (`src/`) with shared domain and service logic used by both the FastAPI web service and background workers.  
- No separate frontend application; any future UI can be layered on top of the stable HTTP API without changing core prediction logic.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| _None_    | N/A        | Current design satisfies constitution gates without exceptions. |
