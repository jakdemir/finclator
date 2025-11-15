# Finclator Operations Runbook

**Last Updated**: 2025-11-15  
**Version**: 1.0.0

---

## Overview

This document describes how to operate and maintain the Finclator system in production, including scheduled jobs, monitoring, and common operational tasks.

---

## Architecture

### Components

1. **FastAPI Web Service** (`finclator-api`)
   - Serves REST API for signals and influencer data
   - Read-only, stateless
   - Port: 8000 (internal), exposed via Render

2. **Scheduled Workers** (Render Cron Jobs)
   - `tweet_ingestion`: Fetches new tweets from X API
   - `sentiment`: Classifies tweet sentiment
   - `price_ingestion`: Fetches OHLCV price data
   - `evaluation`: Evaluates matured predictions
   - `aggregation`: Computes trust-weighted signals

3. **PostgreSQL Database** (`finclator-db`)
   - Single source of truth
   - Stores all tweets, predictions, outcomes, trust scores, signals

---

## Scheduled Jobs

### Recommended Schedule

| Job | Frequency | Command | Purpose |
|-----|-----------|---------|---------|
| **Tweet Ingestion** | Hourly (`:00`) | `python -m src.workers.tweet_ingestion` | Fetch new tweets from X API |
| **Sentiment Classification** | Hourly (`:05`) | `python -m src.workers.sentiment` | Classify unprocessed tweets |
| **Signal Aggregation** | Hourly (`:10`) | `python -m src.workers.aggregation` | Update current signals |
| **Price Ingestion** | Every 6 hours | `python -m src.workers.price_ingestion` | Fetch latest OHLCV data |
| **Prediction Evaluation** | Every 12 hours | `python -m src.workers.evaluation` | Evaluate matured predictions |

### Job Dependencies

```
Tweet Ingestion
    ↓
Sentiment Classification
    ↓
[Wait for predictions to mature]
    ↓
Prediction Evaluation
    ↓
Signal Aggregation → API serves updated signals
```

### Render Cron Jobs Configuration

1. Go to Render Dashboard → Your Service → Cron Jobs
2. Add each job with:
   - **Name**: `finclator-tweet-ingestion`
   - **Command**: `python -m src.workers.tweet_ingestion`
   - **Schedule**: `0 * * * *` (cron expression)
   - **Plan**: Free or Starter

---

## Continuous Calibration

### How Trust Scores Evolve

1. **New Prediction Created**: Trust score unchanged (not yet evaluated)
2. **Prediction Matures**: Evaluation worker compares vs actual prices
3. **Outcome Determined**: CORRECT, WRONG, or UNCLEAR
4. **Trust Score Updated**: Recalculated based on recent outcomes (180-day window)
5. **Signals Recomputed**: Aggregation uses new trust scores

### Trust Score Algorithm

```python
# Simple formula:
correct = count(CORRECT predictions)
wrong = count(WRONG predictions)
unclear = count(UNCLEAR predictions)

# Weight unclear as 0.5
effective_correct = correct + (unclear * 0.5)
effective_wrong = wrong + (unclear * 0.5)

# Normalize to 0-1
score = (effective_correct - effective_wrong) / total
normalized = (score + 1) / 2  # [-1,1] → [0,1]
```

### Triggering Recalculation

**Automatic**: Runs during evaluation worker  
**Manual**:
```bash
# Recompute all influencers
python -m src.workers.recompute_trust_scores

# Recompute specific influencer
python -m src.workers.recompute_trust_scores SantManukyan
```

---

## Monitoring

### Key Metrics to Track

1. **Tweet Ingestion**
   - Tweets fetched per run
   - API rate limit usage
   - Cache hit rate

2. **Sentiment Classification**
   - Tweets processed
   - Predictions generated
   - Classification confidence scores

3. **Prediction Evaluation**
   - Predictions evaluated
   - Outcome distribution (CORRECT/WRONG/UNCLEAR)
   - Trust score changes

4. **Signal Aggregation**
   - Signals computed
   - Signal distribution (BUY/NEUTRAL/SELL)

### Log Patterns to Watch

```bash
# Success patterns
✅ "Tweet ingestion complete - N new tweets ingested"
✅ "Sentiment analysis complete - N tweets processed"
✅ "Evaluation complete - N predictions evaluated"
✅ "Signal aggregation complete - N signals computed"

# Warning patterns
⚠️  "Rate limit exceeded"
⚠️  "🎯 TRUST SCORE CHANGE" (significant change detected)
⚠️  "No signal found" (aggregation not run)

# Error patterns
❌ "Error fetching tweets"
❌ "Classification error"
❌ "Database error"
```

### Health Checks

```bash
# API health
curl https://finclator-api.onrender.com/health

# Database connectivity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tweets;"

# Latest signals timestamp
curl 'https://finclator-api.onrender.com/signals?asset=BTC&horizon=SHORT'
# Check generated_at timestamp is recent
```

---

## Common Operational Tasks

### Adding a New Influencer

1. Edit `data/influencers.json`:
```json
{
  "x": "elonmusk",
  "display_name": "Elon Musk",
  "finance_school": "Growth",
  "notes": "Tesla CEO, crypto influencer"
}
```

2. Run seed script:
```bash
python scripts/seed_data.py
```

3. Wait for next tweet ingestion run (or trigger manually)

### Backfilling Historical Data

1. **Fetch historical tweets**:
```bash
python scripts/fetch_historical_tweets.py
```

2. **Run sentiment classification**:
```bash
python -m src.workers.sentiment
```

3. **Ensure price data exists**:
```bash
python -m src.workers.price_ingestion
```

4. **Evaluate predictions**:
```bash
python -m src.workers.evaluation
```

5. **Recompute trust scores**:
```bash
python -m src.workers.recompute_trust_scores
```

6. **Update signals**:
```bash
python -m src.workers.aggregation
```

### Clearing Cache

```bash
# Clear all API caches
rm -rf .cache/api/

# Clear specific API cache
rm -rf .cache/api/x_api/
rm -rf .cache/api/alphavantage/
rm -rf .cache/api/huggingface/
```

### Database Maintenance

```bash
# Connect to production database
psql $DATABASE_URL

# Check table sizes
SELECT 
    tablename, 
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size
FROM pg_tables 
WHERE schemaname = 'public';

# Clean old trust scores (optional)
DELETE FROM trust_scores WHERE computed_at < NOW() - INTERVAL '90 days';

# Vacuum database
VACUUM ANALYZE;
```

---

## Troubleshooting

### Problem: No tweets being ingested

**Symptoms**: `0 new tweets ingested` every run

**Possible Causes**:
1. X API rate limit exceeded
2. X_API_BEARER_TOKEN invalid/expired
3. Influencers haven't tweeted recently

**Solutions**:
- Check X Developer Portal for rate limit status
- Verify bearer token is valid
- Check influencer X profiles manually

---

### Problem: Signals not updating

**Symptoms**: `generated_at` timestamp is old

**Possible Causes**:
1. Aggregation worker not running
2. No new predictions to aggregate
3. Worker failing silently

**Solutions**:
- Manually run aggregation: `python -m src.workers.aggregation`
- Check worker logs for errors
- Verify predictions exist: `SELECT COUNT(*) FROM sentiment_predictions;`

---

### Problem: Trust scores stuck at 0.5

**Symptoms**: All trust scores = 0.5 (neutral)

**Possible Causes**:
1. No prediction outcomes yet (predictions haven't matured)
2. Evaluation worker not running
3. Insufficient historical data

**Solutions**:
- Check prediction ages: `SELECT MIN(created_at) FROM sentiment_predictions;`
- Run evaluation manually: `python -m src.workers.evaluation`
- Wait for predictions to mature (SHORT=3mo, MEDIUM=12mo, LONG=5y)

---

### Problem: High X API costs

**Symptoms**: Approaching monthly API limit

**Solutions**:
1. Reduce tweet ingestion frequency (every 2-4 hours instead of hourly)
2. Reduce influencer count
3. Increase cache TTL (already 90 days)
4. Upgrade to higher X API tier if needed

---

## Emergency Procedures

### Total System Reset

```bash
# WARNING: This deletes all data!

# 1. Backup database
pg_dump $DATABASE_URL > backup.sql

# 2. Drop and recreate schema
alembic downgrade base
alembic upgrade head

# 3. Reseed data
python scripts/seed_data.py

# 4. Restart workers
# (They will gradually rebuild state)
```

### Rollback Migration

```bash
# Show current migration
alembic current

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>
```

---

## Performance Optimization

### Database Indexes

Already created via Alembic migrations:
- `tweets(tweet_id)` - unique
- `sentiment_predictions(tweet_id)`
- `price_candles(asset_symbol, timestamp)` - unique
- `current_signals(asset_symbol, horizon, finance_school_id)` - unique
- `trust_scores(influencer_id)`

### Query Optimization

- Use connection pooling (asyncpg handles this)
- Limit result sets (already done in code)
- Use database-level aggregations where possible

### Cache Strategy

- X API: 90-day TTL (tweets are immutable)
- Alpha Vantage: 90-day TTL (historical data rarely changes)
- Hugging Face: 90-day TTL (sentiment for same text never changes)

---

## Security

### API Keys

- Store in Render environment variables (not in code)
- Rotate every 90 days
- Use read-only keys where possible

### Database

- Use connection pooling with max connections limit
- Enable SSL for database connections (Render does this automatically)
- Restrict database access to Render services only

### API

- CORS configured for production domains
- Rate limiting (TODO: add if needed)
- No authentication required (read-only public API)

---

## Disaster Recovery

### Backup Strategy

1. **Database backups**: Render auto-backups daily (Starter+ plan)
2. **Manual backup**: `pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql`
3. **Code backups**: Git repository (GitHub)
4. **Configuration backups**: `render.yaml` in Git

### Recovery Procedure

1. Restore database from backup:
```bash
psql $DATABASE_URL < backup.sql
```

2. Verify data integrity:
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM tweets;"
```

3. Run full pipeline:
```bash
./scripts/run_pipeline.sh
```

---

## Contact & Escalation

**On-Call**: (To be defined)  
**Slack Channel**: #finclator-ops  
**Incident Response**: https://your-incident-tracker.com

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-15 | 1.0.0 | Initial runbook created |


