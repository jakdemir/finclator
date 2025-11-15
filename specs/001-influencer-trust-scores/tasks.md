# Tasks: Finclator Influencer Trust-Scoring MVP

**Input**: Design documents from `/Users/jakdemir/projects/finclator/specs/001-influencer-trust-scores/`  
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: No explicit TDD requirement in the spec; basic integration and unit tests may be added as part of implementation where helpful.

**Organization**: Tasks are grouped by phase and user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create backend project structure per implementation plan in `src/` and `tests/` (api, workers, db, services, contract/integration/unit tests).
- [x] T002 Initialize Python project configuration with FastAPI and core dependencies in `pyproject.toml` or `requirements.txt` (FastAPI, SQLAlchemy, asyncpg, HTTPX/requests, Pydantic).
- [x] T003 [P] Configure basic tooling for local development (formatter, linter, type checker) in project root (e.g., `ruff.toml`, `pyproject.toml`, or equivalent).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Define database engine and async session utilities in `src/db/session.py` using `DATABASE_URL`.
- [x] T005 [P] Implement SQLAlchemy models for core entities (Influencer, FinanceSchool, Tweet, SentimentPrediction, PriceCandle, PredictionOutcome, TrustScore, CurrentSignal) in `src/db/models.py` based on `data-model.md`.
- [x] T006 [P] Create Pydantic schemas for API I/O objects (SignalResponse, SchoolSignal, Influencer) in `src/db/schema.py` aligned with `contracts/api.openapi.yaml`.
- [x] T007 Set up Alembic (or equivalent) migrations configuration (`alembic.ini`, `migrations/env.py`) and initial migration for all tables defined in `src/db/models.py`.
- [x] T008 Implement configuration module in `src/services/config.py` to load API keys and environment variables (`DATABASE_URL`, `X_API_KEY`, `ALPHAVANTAGE_API_KEY`, `GROK_API_KEY`).
- [x] T009 [P] Implement HTTP client utilities for external APIs in `src/services/http_client.py` (shared session/retry settings).
- [x] T010 [P] Implement sentiment classifier wrapper in `src/services/sentiment_classifier.py` integrating with grok-3-fast and grok-3-mini for noise filtering and BUY/NEUTRAL/SELL classification.
- [x] T011 [P] Implement price provider abstraction in `src/services/price_provider.py` integrating with Alpha Vantage for BTC, GOLD, and SPX OHLCV data.
- [x] T012 Configure structured logging for pipeline steps and API in `src/services/logging.py` (at minimum, log classification decisions, evaluation results, and aggregation outcomes).

**Checkpoint**: Database schema, configuration, and external service clients are ready; migrations can be applied; no user story code yet.

---

## Phase 3: User Story 1 - View calibrated market indicators (Priority: P1) 🎯 MVP

**Goal**: Allow users to retrieve Buy / Neutral / Sell indicators for BTC, Gold, and S&P 500 across all horizons via a simple API.

**Independent Test**: Using seeded influencers and a populated DB, a user can call `/signals?asset=BTC&horizon=SHORT` (and equivalents) and receive a single indicator and weighted scores per asset/horizon combination.

### Implementation for User Story 1

- [x] T013 [P] [US1] Implement `tweet_ingestion` worker in `src/workers/tweet_ingestion.py` to fetch recent tweets for configured influencers, normalize them, detect referenced assets, and insert new `Tweet` rows marked as unprocessed.
- [x] T014 [P] [US1] Implement `sentiment` worker in `src/workers/sentiment.py` to select unprocessed tweets, call `sentiment_classifier.py`, and create `SentimentPrediction` rows per asset/horizon with BUY/NEUTRAL/SELL labels.
- [x] T015 [P] [US1] Implement `price_ingestion` worker in `src/workers/price_ingestion.py` to fetch and upsert OHLCV data into `PriceCandle` for BTC, GOLD, and SPX via `price_provider.py`.
- [x] T016 [US1] Implement baseline trust scoring logic in `src/services/trust_scoring.py` to compute influencer TrustScore values from PredictionOutcome data (supporting overall and per-asset/horizon scores).
- [x] T017 [US1] Implement `evaluation` worker in `src/workers/evaluation.py` to compute PredictionOutcome rows for matured SentimentPrediction entries (entry/exit prices, return_pct, outcome CORRECT/WRONG/UNCLEAR) and trigger trust-score updates.
- [x] T018 [US1] Implement signal aggregation logic in `src/services/signal_aggregator.py` to compute CurrentSignal rows by combining SentimentPrediction and TrustScore data at asset + horizon + (optional) finance school level.
- [x] T019 [US1] Implement `aggregation` worker in `src/workers/aggregation.py` to run aggregation on a schedule and write/update CurrentSignal rows for all assets and horizons.
- [x] T020 [US1] Implement FastAPI application shell in `src/api/main.py` and dependency wiring in `src/api/dependencies.py` (DB session, configuration).
- [x] T021 [US1] Implement `/signals` endpoint in `src/api/routers/signals.py` to return `SignalResponse` for a given asset and horizon based on CurrentSignal (overall aggregated row).
- [x] T022 [US1] Wire routers into FastAPI app in `src/api/main.py` and verify `/signals` matches `contracts/api.openapi.yaml` schema.

**Checkpoint**: At this point, a full pipeline from ingestion through aggregation exists, and `/signals` returns indicators per asset and horizon using trust-weighted signals (even if trust scores are based on a simple initial algorithm).

---

## Phase 4: User Story 2 - Inspect trust score and school breakdown (Priority: P2)

**Goal**: Allow users to see how indicators are formed, including influencer trust scores, sentiment breakdowns, and finance school contributions.

**Independent Test**: For any indicator visible via `/signals`, a user can retrieve details that show contributing influencers, their trust scores, and school-level BUY/NEUTRAL/SELL contributions.

### Implementation for User Story 2

- [x] T023 [P] [US2] Ensure `FinanceSchool` data and relationships are exposed via Pydantic schemas in `src/db/schema.py` for use in API responses.
- [x] T024 [P] [US2] Extend `signal_aggregator.py` to compute and store school-level CurrentSignal rows (per FinanceSchool) alongside overall rows.
- [x] T025 [US2] Implement `/school-signals` endpoint in `src/api/routers/signals.py` to return an array of SchoolSignal objects per asset and horizon, using finance school–specific CurrentSignal rows.
- [x] T026 [P] [US2] Implement query utilities in `src/services/trust_scoring.py` to fetch current TrustScore values and recent PredictionOutcome history for a given influencer.
- [x] T027 [US2] Implement `/influencers/{id}` endpoint in `src/api/routers/influencers.py` to return influencer details, finance school, current trust scores, and a small list of recent predictions with outcomes.
- [x] T028 [US2] Update API error handling in `src/api/dependencies.py` or a dedicated error module to return clear messages for invalid asset/horizon or unknown influencer IDs.
- [x] T029 [US2] Update API documentation or generated OpenAPI (via FastAPI) to align with `contracts/api.openapi.yaml`, including schema examples for SignalResponse, SchoolSignal, and Influencer.
- [x] T030 [US2] Add minimal integration check (script or manual steps) to verify that `/signals`, `/school-signals`, and `/influencers/{id}` responses are consistent and traceable back to underlying DB data.

**Checkpoint**: At this point, users can understand why a signal is Buy/Neutral/Sell via school-level and influencer-level breakdowns, supporting Data-Driven Trust.

---

## Phase 5: User Story 3 - Continuously calibrate influencer trust scores (Priority: P3)

**Goal**: Automatically recalibrate influencer trust scores based on ongoing prediction performance so that indicators remain up to date and evidence-based over time.

**Independent Test**: Feeding historical data into the pipeline and rerunning jobs adjusts influencer trust scores and signals according to prediction accuracy without manual intervention.

### Implementation for User Story 3

- [x] T031 [P] [US3] Refine trust scoring algorithm in `src/services/trust_scoring.py` to support rolling windows, weighting schemes, and handling of UNCLEAR outcomes (as defined in spec/research).
- [x] T032 [P] [US3] Implement a backfill or replay script in `src/workers/recompute_trust_scores.py` (or similar) to rebuild TrustScore history from PredictionOutcome data for calibration experiments.
- [x] T033 [US3] Configure job scheduling metadata (cron configuration) for Render Cron Jobs to run `tweet_ingestion`, `sentiment`, `price_ingestion`, `evaluation`, and `aggregation` at appropriate intervals (e.g., every few minutes).
- [x] T034 [US3] Implement idempotency and safe re-run behavior in workers (e.g., avoid duplicating tweets, predictions, price candles, and outcomes when jobs overlap).
- [x] T035 [P] [US3] Add logging fields and/or simple audit tables to record when trust scores change significantly for an influencer (e.g., threshold-based events) in `src/services/trust_scoring.py`.
- [x] T036 [US3] Implement simple monitoring hooks (e.g., metrics counters or log summaries) for job success/failure to support basic operational awareness.
- [x] T037 [US3] Validate that repeated runs of the full pipeline (including new data) adjust trust scores and CurrentSignal rows as expected in a controlled historical test scenario.
- [x] T038 [US3] Document operational runbook notes for cron jobs and recalibration behavior in `specs/001-influencer-trust-scores/quickstart.md` (or a short ops section).

**Checkpoint**: At this point, trust scores and signals evolve continuously as new tweets and price data arrive, and the system can be operated via scheduled jobs with basic observability.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and overall developer/user experience.

- [x] T039 [P] Add lightweight developer documentation in `README.md` or `docs/` summarizing the architecture and how to run the Finclator MVP locally and on Render.
- [x] T040 [P] Perform code cleanup and refactoring pass across `src/` to remove duplication and clarify module boundaries (`services`, `workers`, `api`).
- [x] T041 [P] Add basic unit tests for core pure functions (trust scoring rules, aggregation logic, sentiment parsing) in `tests/unit/`.
- [x] T042 [P] Add basic integration tests for end-to-end pipeline (from ingest to `/signals` response) in `tests/integration/test_end_to_end_pipeline.py` using a seeded database.
- [x] T043 Run through `quickstart.md` from a clean environment to ensure all steps work as written and update the doc if deviations are found.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies – must be completed first.  
- **Foundational (Phase 2)**: Depends on Setup completion – BLOCKS all user stories.  
- **User Stories (Phase 3–5)**: All depend on Foundational completion.  
  - User Story 1 (P1) should be implemented first to achieve a working MVP.  
  - User Story 2 (P2) builds on US1 signals to add transparency and breakdowns.  
  - User Story 3 (P3) builds on US1/US2 pipeline to add continuous recalibration.  
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) – provides the core MVP signal retrieval.  
- **User Story 2 (P2)**: Depends on US1’s signals and foundational entities – adds explanation and breakdown capabilities.  
- **User Story 3 (P3)**: Depends on US1 and US2 – extends trust scoring and operational behavior, but does not change API contracts.

### Within Each User Story

- Pipeline components should be implemented in this order: ingestion → sentiment → price → evaluation → trust scoring → aggregation → API surfaces.  
- Configuration and logging must exist before adding complex worker behavior.  
- For US2, ensure aggregation and schemas exist before exposing new endpoints.  
- For US3, ensure base trust scoring is stable before adding recalibration and cron behavior.

### Parallel Opportunities

- All tasks marked `[P]` can be executed in parallel with others in the same phase once their prerequisites (if any) are satisfied.  
- In Foundational, model/schema/clients can be developed in parallel after the DB session module is in place.  
- Within user stories, independent modules (e.g., ingestion vs price ingestion, or endpoints vs logging) can be implemented concurrently by different developers.  
- Unit and integration tests (Phase 6) can be written in parallel with final refactors once primary behavior is stable.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.  
2. Complete Phase 2: Foundational (CRITICAL – blocks all stories).  
3. Complete Phase 3: User Story 1 – end-to-end pipeline and `/signals` endpoint.  
4. **STOP and VALIDATE**: Use `quickstart.md` to confirm indicators are produced for all assets and horizons.  

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready.  
2. Add User Story 1 → Validate core indicators (MVP).  
3. Add User Story 2 → Validate transparency and breakdowns for signals.  
4. Add User Story 3 → Validate continuous recalibration and operational behavior.  
5. Apply Phase 6 polish tasks as time allows.


