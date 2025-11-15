# Quickstart: Finclator Influencer Trust-Scoring MVP

This quickstart describes how to run the core Finclator pipeline end-to-end and verify that indicators are generated for BTC, GOLD, and SPX.

## 1. Prerequisites

- Python 3.11 installed
- PostgreSQL database (e.g., Render PostgreSQL) and connection URL
- API keys:
  - X API (for influencer tweets) or x.ai cookbook stream configuration
  - Alpha Vantage API key (for price data)
  - Access to grok-3-fast and grok-3-mini via an OpenAI-compatible client

Environment variables (example):

- `DATABASE_URL` – PostgreSQL connection string  
- `X_API_KEY` – X API key or bearer token  
- `ALPHAVANTAGE_API_KEY` – Alpha Vantage key  
- `GROK_API_KEY` – API key for grok models  

## 2. Run Database Migrations

Apply the schema for the entities defined in `data-model.md` (Influencer, Tweet, SentimentPrediction, PriceCandle, PredictionOutcome, TrustScore, FinanceSchool, CurrentSignal).

Example:

```bash
alembic upgrade head
```

## 3. Seed Influencers and Finance Schools

Insert a small fixed list of influencer handles and their finance school assignments.

Example (pseudo-CLI):

```bash
python -m src.scripts.seed_influencers
```

## 4. Run Ingestion & Processing Jobs

Run each job once locally (Render will later run these via Cron):

```bash
# 1) Fetch recent tweets for configured influencers
python -m src.workers.tweet_ingestion

# 2) Classify unprocessed tweets into BUY/NEUTRAL/SELL sentiments
python -m src.workers.sentiment

# 3) Fetch and upsert OHLCV price data for BTC, GOLD, SPX
python -m src.workers.price_ingestion

# 4) Evaluate matured predictions as CORRECT/WRONG/UNCLEAR
python -m src.workers.evaluation

# 5) Aggregate trust-weighted signals and write current_signals rows
python -m src.workers.aggregation
```

## 5. Start the API Service

```bash
uvicorn src.api.main:app --reload
```

Verify the API is running at `http://localhost:8000`.

## 6. Validate Indicators

### Get overall signals

```bash
curl "http://localhost:8000/signals?asset=BTC&horizon=SHORT"
```

Expected:

- A JSON object with `asset`, `horizon`, `final_label`, and weighted scores for BUY/NEUTRAL/SELL.

### Get school-level signals

```bash
curl "http://localhost:8000/school-signals?asset=GOLD&horizon=MEDIUM"
```

Expected:

- A JSON array, one entry per finance school, each with its own `final_label` and weighted scores.

### Inspect influencer details

```bash
curl "http://localhost:8000/influencers/{influencer_id}"
```

Expected:

- Influencer handle, finance school, current trust scores, and a small list of recent predictions with outcomes.

## 7. MVP Completion Check

The MVP behavior is considered validated when:

- Indicators exist for BTC, GOLD, and SPX across SHORT, MEDIUM, and LONG horizons.  
- Each indicator can be traced back to trust-weighted influencer predictions and finance school contributions.  
- The full pipeline can be rerun via scheduled jobs without manual intervention.


