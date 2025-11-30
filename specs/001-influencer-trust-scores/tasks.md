# Tasks: Finclator Influencer Trust-Scoring MVP

**Input**: Design documents from `/specs/001-influencer-trust-scores/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in spec, but integration validation is recommended.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify project structure matches plan.md (src/api/, src/db/, src/services/, src/workers/)
- [x] T002 [P] Verify Python 3.11+ and dependencies installed (FastAPI, SQLAlchemy, asyncpg, etc.)
- [x] T003 [P] Verify environment configuration (.env file with DATABASE_URL, API keys)
- [x] T004 Verify database migrations framework (alembic) is configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Verify database schema matches data-model.md (all entities: Influencer, FinanceSchool, Tweet, SentimentPrediction, PriceCandle, PredictionOutcome, TrustScore, CurrentSignal)
- [x] T006 Verify database migrations are applied (alembic upgrade head)
- [x] T007 [P] Verify base models exist in src/db/models.py (all entities with relationships)
- [x] T008 [P] Verify database session management in src/db/session.py
- [x] T009 [P] Verify configuration management in src/services/config.py
- [x] T010 [P] Verify logging setup in src/services/logging.py
- [x] T011 [P] Verify API cache service in src/services/api_cache.py (local filesystem caching)
- [x] T012 [P] Verify HTTP client utilities in src/services/http_client.py
- [x] T013 Verify FastAPI app structure in src/api/main.py (routing, middleware, error handling)
- [x] T014 Verify seed data script exists for influencers and finance schools (or create scripts/seed_data.py)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View calibrated market indicators (Priority: P1) 🎯 MVP

**Goal**: Users can view Buy / Neutral / Sell indicators for BTC, Gold, and S&P 500 across different time horizons via API endpoint.

**Independent Test**: Can be fully tested by calling GET /signals?asset=BTC&horizon=SHORT and verifying that a Buy / Neutral / Sell indicator is returned based on underlying calibrated trust scores and sentiment inputs.

### Implementation for User Story 1

- [x] T015 [US1] Verify CurrentSignal aggregation logic exists in src/services/ (or create signal_aggregator.py)
- [x] T016 [US1] Implement signal aggregation service in src/services/signal_aggregator.py that:
  - Aggregates trust-weighted sentiment within each finance school
  - Aggregates school-level scores into final Buy/Neutral/Sell indicator
  - Writes to CurrentSignal table
- [x] T017 [US1] Implement GET /signals endpoint in src/api/routers/signals.py (or update existing):
  - Query parameters: asset (BTC/GOLD/SPX), horizon (SHORT/MEDIUM/LONG)
  - Returns SignalResponse schema from CurrentSignal table
  - Handles "N/A" case when insufficient data
- [x] T018 [US1] Register /signals router in src/api/main.py
- [x] T019 [US1] Implement Pydantic schema for SignalResponse in src/db/schema.py (matches contracts/api.openapi.yaml)
- [x] T020 [US1] Add error handling for missing data (returns appropriate message per NFR-003)
- [x] T021 [US1] Verify worker script exists to populate CurrentSignal table (or create src/workers/signal_aggregation.py)

**Checkpoint**: At this point, User Story 1 should be fully functional - users can query indicators via API

---

## Phase 4: User Story 2 - Inspect trust score and school breakdown (Priority: P2)

**Goal**: Users can inspect how indicators were formed (influencer trust scores, sentiment breakdown, finance school contributions) via API endpoints.

**Independent Test**: Can be fully tested by calling GET /school-signals?asset=BTC&horizon=SHORT and GET /influencers/{id} and verifying that trust scores, sentiment counts, and school-level contributions are displayed.

### Implementation for User Story 2

- [x] T022 [US2] Implement GET /school-signals endpoint in src/api/routers/signals.py:
  - Query parameters: asset (BTC/GOLD/SPX), horizon (SHORT/MEDIUM/LONG)
  - Returns array of SchoolSignal schema (one per finance school) from CurrentSignal table
  - Filters by finance_school_id (non-null entries)
- [x] T023 [US2] Implement GET /influencers/{id} endpoint in src/api/routers/influencers.py:
  - Path parameter: influencer UUID
  - Returns Influencer schema with current_trust_scores and recent_predictions
  - Includes trust scores from TrustScore table (all horizons, all assets)
  - Includes recent predictions from SentimentPrediction with outcomes
- [x] T024 [US2] Implement Pydantic schemas in src/db/schema.py:
  - SchoolSignal schema (matches contracts/api.openapi.yaml)
  - InfluencerDetail schema with nested trust_scores and recent_predictions
- [x] T025 [US2] Register /school-signals and /influencers routers in src/api/main.py (if not already registered)
- [x] T026 [US2] Add error handling for missing influencer (404) and insufficient data cases
- [x] T027 [US2] Verify influencer router exists in src/api/routers/influencers.py (or create if missing)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - users can view indicators and inspect their breakdown

---

## Phase 5: User Story 3 - Continuously calibrate influencer trust scores (Priority: P3)

**Goal**: System automatically recalibrates influencer trust scores based on observed alignment between sentiment and market movements via weekly batch job.

**Independent Test**: Can be fully tested by running the trust score recalculation worker with historical data and verifying that trust scores update correctly based on prediction accuracy.

### Implementation for User Story 3

- [x] T028 [US3] Verify trust scoring service exists in src/services/trust_scoring.py (already exists, verify completeness)
- [x] T029 [US3] Verify compute_trust_scores_for_influencer function handles all historical data (window_days=None)
- [x] T030 [US3] Create weekly batch job script in src/workers/recompute_trust_scores.py:
  - Iterates through all influencers
  - Calls compute_trust_scores_for_influencer for each (window_days=None for all historical)
  - Persists TrustScore records to database
  - Updates existing scores or creates new ones
- [x] T031 [US3] Add logging to trust score recalculation (influencer processed, scores computed, errors)
- [x] T032 [US3] Verify evaluation worker exists in src/workers/evaluation.py (evaluates matured predictions)
- [x] T033 [US3] Verify evaluation worker creates PredictionOutcome records correctly
- [x] T034 [US3] Create Render.com cron job configuration (or document manual scheduling) for weekly trust score recalculation
- [x] T035 [US3] Add error handling and retry logic for trust score computation failures

**Checkpoint**: All user stories should now be independently functional - system can automatically recalibrate trust scores weekly

---

## Phase 6: Data Pipeline & Integration

**Purpose**: Ensure all data ingestion and processing workers are functional

- [x] T036 [P] Verify tweet ingestion worker in src/workers/tweet_ingestion.py:
  - Fetches tweets from X API (or CSV import)
  - Detects asset symbols
  - Stores in Tweet table
  - Handles rate limits with caching
- [x] T037 [P] Verify sentiment classification worker in src/workers/sentiment.py:
  - Processes unprocessed tweets
  - Extracts sentiment (direction, horizon) using sentiment classifier
  - Creates SentimentPrediction records
  - Marks tweets as processed_for_sentiment=True
- [x] T038 [P] Verify price ingestion worker in src/workers/price_ingestion.py:
  - Fetches price data from Alpha Vantage
  - Stores OHLCV candles in PriceCandle table
  - Handles rate limits with caching
- [x] T039 [P] Verify evaluation worker in src/workers/evaluation.py:
  - Finds matured predictions (matures_at <= now, evaluated=False)
  - Compares sentiment with actual price movements
  - Creates PredictionOutcome records (CORRECT/WRONG/UNCLEAR)
  - Marks predictions as evaluated=True
- [x] T040 Verify MVP pipeline script in scripts/mvp_sant_manukyan.py:
  - Loads CSV data for Sant Manukyan
  - Runs full pipeline: ingestion → sentiment → prices → evaluation → trust scores
  - Can be used for debugging and validation

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T041 [P] Verify API error handling in src/api/errors.py (standardized error responses)
- [x] T042 [P] Add request validation for API endpoints (Pydantic models for query/path parameters)
- [x] T043 [P] Add "last updated" timestamp to API responses when using cached data (per NFR-004)
- [x] T044 [P] Verify rate limit handling in X API client (src/services/x_api_client.py) with exponential backoff
- [x] T045 [P] Verify rate limit handling in price provider (src/services/price_provider.py) with caching
- [x] T046 [P] Add database indexes for performance:
  - Index on CurrentSignal (asset_symbol, horizon, finance_school_id)
  - Index on TrustScore (influencer_id, asset_symbol, horizon)
  - Index on SentimentPrediction (tweet_id, asset_symbol, horizon)
  - Index on PredictionOutcome (sentiment_prediction_id)
- [x] T047 [P] Add logging throughout workers and services (info, warning, error levels)
- [x] T048 [P] Verify environment variable validation in src/services/config.py (required vars, defaults)
- [x] T049 Run quickstart.md validation:
  - Seed influencers and finance schools
  - Run ingestion workers
  - Verify API endpoints return data
  - Test all three user stories end-to-end
- [x] T050 [P] Add API documentation (OpenAPI/Swagger) - verify FastAPI auto-generates from endpoints
- [x] T051 [P] Verify .gitignore includes .env, .cache/, __pycache__/, *.pyc
- [x] T052 [P] Add README updates if needed (API usage examples, worker scheduling)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Data Pipeline (Phase 6)**: Can run in parallel with user stories (different components)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 for CurrentSignal data structure
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent but benefits from US1/US2 data

### Within Each User Story

- Models/entities must exist (from Foundational phase)
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, user stories can start in parallel (if team capacity allows)
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members
- Data Pipeline tasks (Phase 6) can run in parallel with user story implementation

---

## Parallel Example: User Story 1

```bash
# Launch foundational verification tasks in parallel:
Task: "Verify base models exist in src/db/models.py"
Task: "Verify database session management in src/db/session.py"
Task: "Verify configuration management in src/services/config.py"
Task: "Verify logging setup in src/services/logging.py"

# Launch US1 implementation tasks in parallel (after foundational):
Task: "Implement signal aggregation service in src/services/signal_aggregator.py"
Task: "Implement Pydantic schema for SignalResponse in src/db/schema.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Seed data (influencers, tweets, sentiments, prices, outcomes)
   - Run signal aggregation
   - Test GET /signals endpoint
   - Verify Buy/Neutral/Sell indicators display correctly
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add Data Pipeline → Test end-to-end → Deploy/Demo
6. Add Polish → Final validation → Production ready
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (signals endpoint)
   - Developer B: User Story 2 (school-signals, influencers endpoints)
   - Developer C: User Story 3 (trust score recalculation)
   - Developer D: Data Pipeline (workers)
3. Stories complete and integrate independently
4. Polish phase: team collaboration on cross-cutting concerns

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Many components already exist - tasks focus on verification and completion
- MVP focuses on single influencer (Sant Manukyan) per FR-101
- CSV import utility (scripts/load_tweets_from_file.py) exists for offline data
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

