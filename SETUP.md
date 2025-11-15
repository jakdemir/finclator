# Local Setup Guide for Finclator

This guide will help you run Finclator locally for development and testing.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or higher** installed
- **PostgreSQL** installed and running
- **API Keys** (optional for initial testing):
  - X API key (for tweet ingestion)
  - Alpha Vantage API key (for price data)
  - grok API key (for sentiment classification)

## Step 1: Clone and Install

```bash
# Navigate to project directory
cd /Users/jakdemir/projects/finclator

# Create a virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -e ".[dev]"
```

## Step 2: Set Up PostgreSQL Database

### Option A: Using PostgreSQL locally

```bash
# Create database
createdb finclator

# Verify connection
psql -d finclator -c "SELECT version();"
```

### Option B: Using Docker

```bash
docker run -d \
  --name finclator-db \
  -e POSTGRES_DB=finclator \
  -e POSTGRES_USER=finclator \
  -e POSTGRES_PASSWORD=finclator123 \
  -p 5432:5432 \
  postgres:15
```

## Step 3: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Minimal `.env` for local testing:**

```env
# Database (adjust if using Docker or different credentials)
DATABASE_URL=postgresql+asyncpg://localhost/finclator

# API Keys (can be dummy values for testing structure)
X_API_KEY=dummy_key_for_testing
ALPHAVANTAGE_API_KEY=dummy_key_for_testing
GROK_API_KEY=dummy_key_for_testing

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

**Note**: The workers will log warnings about missing real API keys but will still demonstrate the pipeline structure.

## Step 4: Run Database Migrations

```bash
# Apply all migrations to create tables
alembic upgrade head

# Verify tables were created
psql -d finclator -c "\dt"
```

You should see tables: `influencers`, `finance_schools`, `tweets`, `sentiment_predictions`, `price_candles`, `prediction_outcomes`, `trust_scores`, `current_signals`

## Step 5: Seed Initial Data

```bash
# Create finance schools and sample influencers
python scripts/seed_data.py
```

This creates:
- 4 finance schools (Macro, Technical, Value, Growth)
- 4 sample influencers (one per school)

**Important**: Edit `scripts/seed_data.py` to replace example handles with real X influencer handles if you have X API access.

## Step 6: Run the Pipeline

You have two options:

### Option A: Run Full Pipeline Script

```bash
# Run all workers in sequence
./scripts/run_pipeline.sh
```

This executes:
1. Tweet ingestion
2. Sentiment classification
3. Price data ingestion
4. Prediction evaluation
5. Signal aggregation

### Option B: Run Workers Individually

```bash
# 1. Ingest tweets
python -m src.workers.tweet_ingestion

# 2. Classify sentiment
python -m src.workers.sentiment

# 3. Fetch price data
python -m src.workers.price_ingestion

# 4. Evaluate predictions
python -m src.workers.evaluation

# 5. Aggregate signals
python -m src.workers.aggregation
```

## Step 7: Start the API

```bash
# Start FastAPI server
uvicorn src.api.main:app --reload

# Server will start at http://localhost:8000
```

## Step 8: Test the API

### Using cURL:

```bash
# Get BTC short-term signal
curl "http://localhost:8000/signals?asset=BTC&horizon=SHORT"

# Get Gold medium-term signal
curl "http://localhost:8000/signals?asset=GOLD&horizon=MEDIUM"

# Get S&P 500 long-term signal
curl "http://localhost:8000/signals?asset=SPX&horizon=LONG"
```

### Using your browser:

- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

### Expected Response:

```json
{
  "asset": "BTC",
  "horizon": "SHORT",
  "final_label": "NEUTRAL",
  "weighted_score_buy": 0.33,
  "weighted_score_neutral": 0.34,
  "weighted_score_sell": 0.33,
  "generated_at": "2025-11-15T12:34:56.789Z"
}
```

## Troubleshooting

### Database Connection Error

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution**: Verify PostgreSQL is running and DATABASE_URL is correct:
```bash
psql -d finclator  # Test connection
```

### Import Errors

```
ModuleNotFoundError: No module named 'src'
```

**Solution**: Install the package in development mode:
```bash
pip install -e .
```

### No Signals Available

```
404: No signal found for BTC/SHORT
```

**Solution**: Run the pipeline workers first:
```bash
./scripts/run_pipeline.sh
```

### Workers Return Empty Results

This is **expected** on first run if:
- Using dummy API keys (no real data fetched)
- No tweets ingested yet
- Price data not available

**For testing with real data**, add actual API keys to `.env` and update influencer handles in `scripts/seed_data.py`.

## Development Workflow

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

### Reset Database (for testing)

```bash
# Drop and recreate database
dropdb finclator
createdb finclator

# Reapply migrations and seed data
alembic upgrade head
python scripts/seed_data.py
```

## Next Steps

1. **Add Real Influencers**: Edit `scripts/seed_data.py` with actual X handles
2. **Configure Real API Keys**: Update `.env` with valid keys for X, Alpha Vantage, and grok
3. **Run Pipeline Regularly**: Set up cron jobs or use Render Cron Jobs in production
4. **Monitor Logs**: Watch for classification decisions, evaluation results, and signal updates

## Getting Help

- See `README.md` for architecture overview
- See `specs/001-influencer-trust-scores/quickstart.md` for deployment details
- Check logs at `LOG_LEVEL=DEBUG` for detailed information

## Production Deployment

For deploying to Render, see:
- `specs/001-influencer-trust-scores/plan.md` - Architecture
- `specs/001-influencer-trust-scores/quickstart.md` - Deployment steps

