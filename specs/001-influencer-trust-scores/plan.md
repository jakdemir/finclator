# Implementation Plan: Finclator Influencer Trust-Scoring MVP

**Branch**: `001-influencer-trust-scores` | **Date**: 2025-11-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-influencer-trust-scores/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Finclator generates Buy / Neutral / Sell market indicators for BTC, Gold, and S&P 500 by analyzing influencer tweets, extracting sentiment signals (direction and time horizon), comparing predictions against actual market movements, and computing performance-based trust scores. The system groups influencers by finance theory schools and aggregates trust-weighted sentiment to produce calibrated indicators. Technical approach: Python 3.11 with FastAPI for the read-only API, SQLAlchemy + asyncpg for PostgreSQL, worker scripts for async ingestion/processing, and external integrations (X API, Alpha Vantage, Hugging Face) with local caching to handle rate limits.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI 0.104+, SQLAlchemy 2.0+, asyncpg 0.29+, uvicorn, httpx, pydantic, alembic  
**Storage**: PostgreSQL (async via asyncpg)  
**Testing**: pytest 7.4+, pytest-asyncio  
**Target Platform**: Linux server (Render.com deployment)  
**Project Type**: Single project (web API + background workers)  
**Performance Goals**: Handle 50+ influencers, 10,000+ tweets/month ingestion; API response <500ms p95; weekly batch trust score recalculation  
**Constraints**: Rate-limited external APIs (X API: 50 req/15min free tier; Alpha Vantage: 5 req/min free tier); must use cached data when APIs unavailable; minimal UI (read-only API endpoints)  
**Scale/Scope**: MVP focused on single influencer (Sant Manukyan) for initial validation; designed to scale to 50+ influencers, 10,000+ tweets/month

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity & Focus

✅ **PASS**: MVP is minimal and focused:
- Core prediction logic: sentiment extraction → evaluation → trust scoring → aggregation
- Data acquisition: tweet ingestion, price data fetching, sentiment classification
- No user accounts, authentication, or complex UI/UX
- Single influencer (Sant Manukyan) for initial validation
- Read-only API with minimal endpoints
- Background workers for async processing

**Rationale Compliance**: All features directly contribute to prediction accuracy (sentiment analysis, trust scoring) or data quality (ingestion, price data). Non-essential features deferred.

### II. Data-Driven Trust

✅ **PASS**: Trust score methodology is transparent and auditable:
- Trust scores computed from historical prediction outcomes (CORRECT/WRONG/UNCLEAR)
- Each indicator traceable back to underlying sentiments and performance evaluations
- API endpoints expose influencer trust scores and school-level breakdowns
- Database schema supports full audit trail (Tweet → SentimentPrediction → PredictionOutcome → TrustScore)

**Rationale Compliance**: Methodology is verifiable and grounded in measurable data sources (influencer sentiment, historical market performance). No over-documentation; implementation is self-documenting through code structure.

### Post-Design Re-evaluation

✅ **PASS**: Design maintains simplicity:
- Single project structure (no separate frontend/backend projects)
- Direct database access via SQLAlchemy (no repository pattern abstraction)
- Simple worker scripts (no complex orchestration framework)
- Minimal API surface (3 endpoints: signals, school-signals, influencers/{id})

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── api/                    # FastAPI application
│   ├── main.py            # FastAPI app entry point
│   ├── routers/           # API route handlers
│   │   └── influencers.py
│   ├── dependencies.py    # Dependency injection
│   ├── errors.py          # Error handlers
│   └── static/            # Static files (if any)
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy ORM models
│   ├── schema.py          # Pydantic schemas
│   └── session.py         # Database session management
├── services/              # Business logic services
│   ├── config.py          # Configuration management
│   ├── logging.py         # Logging setup
│   ├── x_api_client.py    # X API integration
│   ├── price_provider.py  # Alpha Vantage integration
│   ├── sentiment_classifier.py  # Hugging Face integration
│   ├── trust_scoring.py   # Trust score calculation
│   ├── api_cache.py       # Local filesystem caching
│   └── http_client.py     # HTTP client utilities
└── workers/               # Background job scripts
    ├── tweet_ingestion.py    # Fetch tweets from X API
    ├── sentiment.py         # Classify tweet sentiment
    ├── price_ingestion.py    # Fetch price data
    └── evaluation.py        # Evaluate predictions

tests/
├── unit/                  # Unit tests
├── integration/           # Integration tests
└── contract/             # Contract tests (if any)

scripts/                   # Utility scripts
├── mvp_sant_manukyan.py  # MVP pipeline script
├── get_recent_tweets.py  # Tweet fetching utility
└── load_tweets_from_file.py  # CSV import utility

alembic/                   # Database migrations
.env                       # Environment variables
pyproject.toml            # Python project configuration
```

**Structure Decision**: Single project structure (Option 1) selected. This is a web API with background workers, all in one codebase. No separate frontend or mobile apps. The structure separates concerns: `api/` for HTTP endpoints, `db/` for data access, `services/` for business logic, and `workers/` for async background jobs. This aligns with the "Simplicity & Focus" principle by avoiding unnecessary project splits.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All design decisions align with Constitution principles:
- Single project structure (no multi-project complexity)
- Direct SQLAlchemy access (no repository pattern abstraction)
- Simple worker scripts (no complex orchestration)
- Minimal API surface (3 endpoints)
- Local filesystem caching (no Redis/complex cache layer)
