# Finclator

Trust-scoring system that generates Buy / Neutral / Sell market indicators for BTC, Gold, and the S&P 500 by analyzing influencer sentiment and calibrating it against historical market performance.

## Features

- **Trust-Scored Indicators**: Calibrated Buy/Neutral/Sell signals per asset and time horizon
- **Influencer Sentiment Analysis**: Automated extraction and classification of market predictions from tweets
- **Performance-Based Calibration**: Trust scores that increase with prediction accuracy
- **Finance School Grouping**: Insights organized by conceptual worldview (macro, technical, value, etc.)
- **Transparent Methodology**: Auditable trail from tweets → sentiment → outcomes → trust scores → signals

## Architecture

### Core Components

- **FastAPI Service**: Read-only API exposing calibrated indicators
- **Worker Scripts**: Scheduled jobs for ingestion, sentiment analysis, price data, evaluation, and aggregation
- **PostgreSQL Database**: Single source of truth for all entities and relationships
- **External Integrations**:
  - **X API v2** for influencer tweets
  - **Alpha Vantage** for OHLCV price data (BTC, Gold via GLD, S&P 500 via SPY)
  - **Hugging Face** for sentiment classification (FinBERT model)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (local or Render-managed)
- API keys:
  - **X API** (Twitter Bearer Token) - [Setup Guide](docs/X_API_SETUP.md)
  - **Alpha Vantage API Key** - [Get Free Key](https://www.alphavantage.co/support/#api-key)
  - **Hugging Face API Token** (optional, free tier available) - [Get Token](https://huggingface.co/settings/tokens)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd finclator
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and database URL
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Seed influencers and finance schools (see `specs/001-influencer-trust-scores/quickstart.md`)

### Running Workers

Execute workers manually or via Render Cron Jobs:

```bash
# Fetch tweets
python -m src.workers.tweet_ingestion

# Classify sentiment
python -m src.workers.sentiment

# Fetch price data
python -m src.workers.price_ingestion

# Evaluate predictions
python -m src.workers.evaluation

# Aggregate signals
python -m src.workers.aggregation
```

### Running the API

```bash
uvicorn src.api.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Example API Calls

Get signal for BTC short-term:
```bash
curl "http://localhost:8000/signals?asset=BTC&horizon=SHORT"
```

Response:
```json
{
  "asset": "BTC",
  "horizon": "SHORT",
  "final_label": "BUY",
  "weighted_score_buy": 0.65,
  "weighted_score_neutral": 0.20,
  "weighted_score_sell": 0.15,
  "generated_at": "2025-11-15T12:34:56"
}
```

## Project Structure

```
src/
├── api/              # FastAPI application
│   ├── main.py       # App entry point
│   ├── dependencies.py
│   └── routers/
│       └── signals.py
├── workers/          # Background jobs
│   ├── tweet_ingestion.py
│   ├── sentiment.py
│   ├── price_ingestion.py
│   ├── evaluation.py
│   └── aggregation.py
├── db/              # Database layer
│   ├── models.py    # SQLAlchemy models
│   ├── schema.py    # Pydantic schemas
│   └── session.py   # DB session management
└── services/        # Business logic
    ├── config.py
    ├── http_client.py
    ├── sentiment_classifier.py
    ├── price_provider.py
    ├── trust_scoring.py
    ├── signal_aggregator.py
    └── logging.py

tests/
├── contract/        # API contract tests
├── integration/     # End-to-end tests
└── unit/           # Unit tests
```

## Development

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## Deployment

See `specs/001-influencer-trust-scores/quickstart.md` for detailed deployment instructions on Render.

### Key Configuration

- **Database**: Render PostgreSQL (single primary database)
- **API Service**: Render Web Service running `uvicorn src.api.main:app`
- **Workers**: Render Cron Jobs executing workers on schedule
- **Environment Variables**: Configure via Render dashboard

## Constitution Alignment

This MVP strictly adheres to the Finclator Constitution:

1. **Simplicity & Focus**: No user accounts, no complex UI—only core prediction logic and data acquisition
2. **Data-Driven Trust**: Transparent, auditable methodology directly linking sentiment to performance

## License

[Add license information]

## Support

For questions or issues, refer to `specs/001-influencer-trust-scores/` documentation.

