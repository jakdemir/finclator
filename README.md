# Finclator

Trust-scoring system that generates Buy / Neutral / Sell market indicators for BTC, Gold, and the S&P 500 on short medium and and long term by analyzing influencer sentiment and calibrating it against historical market performance.

## Project Status

**⚠️ PROJECT ABANDONED**

This project is being aborted because **sentiments of users are not clear**. The sentiment classification from tweets does not reliably extract actionable market signals, making the trust-scoring system ineffective. On the other hand, grok may help more reasonable data. https://grok.com/c/e4a937b4-ae53-4786-91e7-95324f30d75d

## Architecture

### Core Components

- **FastAPI Service**: Read-only API exposing calibrated indicators
- **Worker Scripts**: Scheduled jobs for ingestion, sentiment analysis, price data, evaluation, and aggregation
- **PostgreSQL Database**: Single source of truth for all entities and relationships
- **External Integrations**:
  - **X API v2** for influencer tweets
  - **Alpha Vantage** for OHLCV price data (BTC, Gold via GLD, S&P 500 via SPY)
  - **Hugging Face / OpenAI** for sentiment classification

## End-to-End Process Flow

### Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FINCLATOR PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────┘

    [TwExportly]                    [External APIs]
         │                                │
         │ CSV Export                    │
         ▼                                │
    ┌─────────┐                          │
    │  CSV    │                          │
    │  Files  │                          │
    └────┬────┘                          │
         │                                │
         │ load_tweets_from_csv.py        │
         ▼                                │
    ┌─────────────────────────────────────┴──────────┐
    │         PostgreSQL Database                     │
    │  ┌──────────┐  ┌──────────────────┐           │
    │  │ Tweets   │  │ SentimentPreds   │           │
    │  └────┬─────┘  └────────┬─────────┘           │
    │       │                 │                      │
    │       │ sentiment.py    │                      │
    │       │ (HuggingFace/   │                      │
    │       │  OpenAI Agent)  │                      │
    │       ▼                 ▼                      │
    │  ┌──────────────────────────────────┐         │
    │  │   SentimentPredictions            │         │
    │  └───────┬──────────────────────────┘         │
    │          │                                      │
    │          │ price_ingestion.py                  │
    │          │ (Alpha Vantage API)                 │
    │          ▼                                      │
    │  ┌──────────────────────────────────┐         │
    │  │      PriceCandles                 │         │
    │  └───────┬──────────────────────────┘         │
    │          │                                      │
    │          │ evaluation.py                       │
    │          │ (Compare predictions vs reality)     │
    │          ▼                                      │
    │  ┌──────────────────────────────────┐         │
    │  │   PredictionOutcomes             │         │
    │  │   (CORRECT/WRONG/UNCLEAR)        │         │
    │  └───────┬──────────────────────────┘         │
    │          │                                      │
    │          │ recompute_trust_scores.py           │
    │          │ (Calculate performance scores)      │
    │          ▼                                      │
    │  ┌──────────────────────────────────┐         │
    │  │      TrustScores                 │         │
    │  │  (per influencer/asset/horizon)   │         │
    │  └───────┬──────────────────────────┘         │
    │          │                                      │
    │          │ signal_aggregation.py               │
    │          │ (Weighted aggregation)               │
    │          ▼                                      │
    │  ┌──────────────────────────────────┐         │
    │  │    CurrentSignals                 │         │
    │  │  (Buy/Neutral/Sell indicators)    │         │
    │  └───────┬──────────────────────────┘         │
    │          │                                      │
    └──────────┼──────────────────────────────────────┘
               │
               │ FastAPI
               ▼
    ┌──────────────────────┐
    │   Dashboard & API   │
    │  /dashboard          │
    │  /signals            │
    │  /influencers        │
    └──────────────────────┘
```

### 1. Tweet Ingestion
- Export tweets from influencers using **TwExportly** (Chrome extension)
- CSV files saved to `data/TwExportly_username_tweets_YYYY_MM_DD.csv`
- Load tweets into database: `python scripts/load_tweets_from_csv.py data/file.csv username`

### 2. Sentiment Analysis
- Process unprocessed tweets: `python -m src.workers.sentiment`
- Classify sentiment (BUY/NEUTRAL/SELL) and detect time horizon (SHORT/MEDIUM/LONG)
- Uses HuggingFace models or OpenAI agent-based classification
- Creates `SentimentPrediction` records

### 3. Price Data Ingestion
- Fetch historical price data: `python -m src.workers.price_ingestion`
- Updates `PriceCandle` table with OHLCV data for BTC, GOLD, SPX

### 4. Prediction Evaluation
- Evaluate matured predictions: `python -m src.workers.evaluation`
- Compares predicted direction with actual market movements
- Creates `PredictionOutcome` records (CORRECT/WRONG/UNCLEAR)

### 5. Trust Score Calculation
- Recalculate trust scores: `python -m src.workers.recompute_trust_scores`
- Computes performance-based scores per influencer, asset, and horizon
- Updates `TrustScore` table

### 6. Signal Aggregation
- Aggregate trust-weighted signals: `python -m src.workers.signal_aggregation`
- Combines influencer predictions weighted by trust scores
- Generates final Buy/Neutral/Sell indicators in `CurrentSignal` table

### 7. Dashboard & API
- View dashboard: `http://localhost:8000/dashboard`
- API endpoints: `/signals`, `/influencers`, `/api/dashboard/*`

## My Routine

1. **Export tweets** using TwExportly → `data/TwExportly_username_tweets_YYYY_MM_DD.csv`

2. **Load tweets**: 
   ```bash
   python scripts/load_tweets_from_csv.py data/TwExportly_username_tweets_YYYY_MM_DD.csv username
   ```

3. **Run full pipeline**:
   ```bash
   python -m src.workers.sentiment \
   && python -m src.workers.price_ingestion \
   && python -m src.workers.evaluation \
   && python -m src.workers.recompute_trust_scores \
   && python -m src.workers.signal_aggregation
   ```

4. **Check database view**:
   ```sql
   SELECT * FROM debug_pipeline WHERE handle = 'username' LIMIT 100;
   ```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- API keys in `.env`:
  - `X_API_BEARER_TOKEN` (optional - using TwExportly instead)
  - `ALPHAVANTAGE_API_KEY`
  - `HUGGINGFACE_API_KEY` or `OPENAI_API_KEY` (for sentiment)

### Setup

```bash
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_data.py
```

### Run Pipeline

See "My Routine" section above.

### Start API

```bash
uvicorn src.api.main:app --reload
```

Dashboard: http://localhost:8000/dashboard

## Current Influencers

- `@SantManukyan` - Sant Manukyan (1002 tweets)
- `@laplace2011` - Devrim Akyil (989 tweets)
- `@APompliano` - Anthony Pompliano (309 tweets)

## Database Debug View

```sql
CREATE OR REPLACE VIEW debug_pipeline AS
SELECT
    i.handle,
    t.tweet_id,
    t.text,
    sp.asset_symbol,
    sp.direction,
    sp.horizon,
    po.outcome,
    ts.score as trust_score,
    cs.final_label as signal_label
FROM influencers i
LEFT JOIN tweets t ON i.id = t.influencer_id
LEFT JOIN sentiment_predictions sp ON t.id = sp.tweet_id
LEFT JOIN prediction_outcomes po ON sp.id = po.sentiment_prediction_id
LEFT JOIN trust_scores ts ON i.id = ts.influencer_id
LEFT JOIN current_signals cs ON sp.asset_symbol = cs.asset_symbol AND sp.horizon = cs.horizon
ORDER BY i.handle, t.tweeted_at DESC;
```

