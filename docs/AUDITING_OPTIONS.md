# Finclator Auditing & Monitoring Options

**Last Updated**: 2025-11-15  
**Version**: 1.0.0

---

## 🎯 Overview

This guide covers all available options for auditing, monitoring, and inspecting the Finclator system.

---

## 1. 🌐 Web-Based Auditing (Easiest)

### A. Admin API Endpoints (NEW! ⭐)

**Base URL**: `http://localhost:8000/admin`

#### Database Statistics
```bash
curl http://localhost:8000/admin/stats | jq
```
**Shows**: Row counts for all tables, tweets by asset, processing status

#### Recent Tweets
```bash
curl 'http://localhost:8000/admin/tweets?limit=10' | jq
```
**Shows**: Latest tweets with influencer info, text, assets, processing status

#### Recent Predictions
```bash
curl 'http://localhost:8000/admin/predictions?limit=10' | jq
```
**Shows**: Sentiment predictions with confidence scores, assets, horizons

#### Price Data
```bash
curl 'http://localhost:8000/admin/price-candles?asset=BTC&limit=10' | jq
```
**Shows**: Latest OHLCV candles for specified asset

#### Trust Scores
```bash
curl http://localhost:8000/admin/trust-scores | jq
```
**Shows**: All current trust scores by influencer, asset, horizon

#### Prediction Outcomes
```bash
curl 'http://localhost:8000/admin/outcomes?limit=10' | jq
```
**Shows**: Evaluated predictions with accuracy results

#### Pipeline Status
```bash
curl http://localhost:8000/admin/pipeline-status | jq
```
**Shows**: 
- Activity in last 24 hours
- Latest timestamps for each pipeline stage
- Processing throughput

### B. Interactive API Documentation

**URL**: `http://localhost:8000/docs`

- Test all admin endpoints interactively
- See response schemas
- Try different parameters

---

## 2. 🗄️ Database Direct Access

### A. PostgreSQL CLI (psql)

#### Connect to Database
```bash
# Local
psql finclator

# Or with full connection string
psql "postgresql://localhost/finclator"

# Render (production)
psql $DATABASE_URL
```

#### Useful Queries

**Table Sizes:**
```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size,
    n_live_tup as rows
FROM pg_tables t
JOIN pg_stat_user_tables s ON t.tablename = s.relname
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

**Row Counts:**
```sql
SELECT 'finance_schools' AS table, COUNT(*) FROM finance_schools
UNION ALL
SELECT 'influencers', COUNT(*) FROM influencers
UNION ALL
SELECT 'tweets', COUNT(*) FROM tweets
UNION ALL
SELECT 'sentiment_predictions', COUNT(*) FROM sentiment_predictions
UNION ALL
SELECT 'price_candles', COUNT(*) FROM price_candles
UNION ALL
SELECT 'prediction_outcomes', COUNT(*) FROM prediction_outcomes
UNION ALL
SELECT 'trust_scores', COUNT(*) FROM trust_scores
UNION ALL
SELECT 'current_signals', COUNT(*) FROM current_signals;
```

**Recent Activity:**
```sql
-- Latest tweets
SELECT 
    t.tweet_id,
    i.handle,
    t.text,
    t.tweeted_at,
    t.processed_for_sentiment
FROM tweets t
JOIN influencers i ON t.influencer_id = i.id
ORDER BY t.tweeted_at DESC
LIMIT 10;

-- Latest predictions
SELECT 
    sp.asset_symbol,
    sp.direction,
    sp.horizon,
    sp.confidence,
    i.handle,
    sp.created_at
FROM sentiment_predictions sp
JOIN tweets t ON sp.tweet_id = t.id
JOIN influencers i ON t.influencer_id = i.id
ORDER BY sp.created_at DESC
LIMIT 10;

-- Trust scores by influencer
SELECT 
    i.handle,
    i.display_name,
    ts.asset_symbol,
    ts.horizon,
    ts.score,
    ts.computed_at
FROM trust_scores ts
JOIN influencers i ON ts.influencer_id = i.id
ORDER BY ts.computed_at DESC;
```

**Data Quality Checks:**
```sql
-- Check for tweets without predictions
SELECT COUNT(*)
FROM tweets
WHERE processed_for_sentiment = TRUE
AND id NOT IN (SELECT DISTINCT tweet_id FROM sentiment_predictions);

-- Check for zero prices
SELECT asset_symbol, COUNT(*)
FROM price_candles
WHERE close = 0 OR open = 0
GROUP BY asset_symbol;

-- Check trust score distribution
SELECT 
    CASE 
        WHEN score < 0.3 THEN 'Low (< 0.3)'
        WHEN score < 0.5 THEN 'Below Average (0.3-0.5)'
        WHEN score < 0.7 THEN 'Above Average (0.5-0.7)'
        ELSE 'High (>= 0.7)'
    END as score_range,
    COUNT(*)
FROM trust_scores
GROUP BY score_range;
```

### B. pgAdmin (Visual Database Tool)

**Install:**
```bash
# Mac
brew install --cask pgadmin4

# Or download from: https://www.pgadmin.org/download/
```

**Connect:**
1. Open pgAdmin
2. Add New Server
3. Connection tab:
   - Host: `localhost`
   - Port: `5432`
   - Database: `finclator`
   - Username: your postgres user

**Features:**
- Visual query builder
- Table data viewer
- Query history
- Export to CSV/JSON
- Schema diagrams

### C. DBeaver (Universal Database Tool)

**Download**: https://dbeaver.io/download/

**Features:**
- Works with any database
- ER diagrams
- Data editor
- SQL formatting
- Export options

---

## 3. 🐍 Python Scripts

### A. Custom Validation Script

```python
# scripts/audit_database.py
import asyncio
from src.db.session import AsyncSessionLocal
from src.db.models import *
from sqlalchemy import select, func

async def audit():
    async with AsyncSessionLocal() as session:
        # Get all counts
        tables = [FinanceSchool, Influencer, Tweet, 
                 SentimentPrediction, PriceCandle, 
                 PredictionOutcome, TrustScore, CurrentSignal]
        
        for model in tables:
            count = await session.execute(
                select(func.count()).select_from(model)
            )
            print(f"{model.__tablename__}: {count.scalar()}")

asyncio.run(audit())
```

### B. Data Export Script

```python
# scripts/export_data.py
import asyncio
import pandas as pd
from src.db.session import AsyncSessionLocal
from src.db.models import Tweet, Influencer
from sqlalchemy import select

async def export_tweets_to_csv():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tweet, Influencer.handle)
            .join(Influencer)
        )
        
        data = []
        for tweet, handle in result.all():
            data.append({
                'handle': handle,
                'text': tweet.text,
                'tweeted_at': tweet.tweeted_at,
                'assets': ','.join(tweet.asset_symbols)
            })
        
        df = pd.DataFrame(data)
        df.to_csv('tweets_export.csv', index=False)
        print(f"Exported {len(df)} tweets")

asyncio.run(export_tweets_to_csv())
```

---

## 4. 📊 Monitoring & Logging

### A. Application Logs

**View Logs:**
```bash
# Real-time
tail -f logs/finclator.log

# Last 100 lines
tail -n 100 logs/finclator.log

# Search for errors
grep ERROR logs/finclator.log

# Search for specific influencer
grep "@SantManukyan" logs/finclator.log
```

**Log Patterns:**
- `INFO` - Normal operations
- `WARNING` - Non-critical issues (e.g., trust score changes)
- `ERROR` - Problems that need attention

### B. System Monitoring

**Check Running Processes:**
```bash
ps aux | grep python | grep finclator
```

**Check Port Usage:**
```bash
lsof -i :8000
```

**Monitor Resource Usage:**
```bash
# CPU & Memory
top -p $(pgrep -f "uvicorn src.api.main")

# Or with htop (install: brew install htop)
htop -p $(pgrep -f "uvicorn")
```

---

## 5. 🔧 CLI Tools

### A. Validation Script (Already Created)

```bash
python scripts/validate_mvp.py
```

**Checks:**
- File existence
- Database integrity
- Relationship validity
- Data quality

### B. Custom Query Tool

Create `scripts/quick_query.py`:
```python
#!/usr/bin/env python3
import asyncio
import sys
from src.db.session import AsyncSessionLocal
from sqlalchemy import text

async def query(sql):
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql))
        for row in result:
            print(row)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/quick_query.py 'SELECT ...'")
        sys.exit(1)
    
    asyncio.run(query(sys.argv[1]))
```

**Usage:**
```bash
python scripts/quick_query.py "SELECT COUNT(*) FROM tweets"
```

---

## 6. 📈 Visualization Tools

### A. Jupyter Notebook

**Setup:**
```bash
pip install jupyter pandas matplotlib seaborn

jupyter notebook
```

**Example Notebook:**
```python
import pandas as pd
from sqlalchemy import create_engine

# Connect
engine = create_engine('postgresql://localhost/finclator')

# Load data
df_tweets = pd.read_sql("SELECT * FROM tweets", engine)
df_predictions = pd.read_sql("SELECT * FROM sentiment_predictions", engine)

# Analyze
print(df_tweets.describe())
print(df_predictions['direction'].value_counts())

# Visualize
df_predictions['direction'].value_counts().plot(kind='bar')
```

### B. Metabase (Open Source BI Tool)

**Install with Docker:**
```bash
docker run -d -p 3000:3000 \
  -e "MB_DB_TYPE=postgres" \
  -e "MB_DB_DBNAME=finclator" \
  -e "MB_DB_PORT=5432" \
  -e "MB_DB_USER=postgres" \
  -e "MB_DB_PASS=yourpass" \
  -e "MB_DB_HOST=host.docker.internal" \
  --name metabase metabase/metabase
```

**Access**: `http://localhost:3000`

**Features:**
- Drag-and-drop dashboards
- SQL editor
- Charts and visualizations
- Scheduled reports

### C. Grafana + PostgreSQL

**For production monitoring:**
- Time-series metrics
- Alerts
- Multiple data sources
- Beautiful dashboards

---

## 7. 🔍 Performance Profiling

### A. Query Performance

```sql
-- Enable query timing
\timing

-- Explain analyze
EXPLAIN ANALYZE
SELECT * FROM tweets WHERE processed_for_sentiment = FALSE;

-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### B. Database Stats

```sql
-- Cache hit ratio (should be > 90%)
SELECT 
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_hit_ratio
FROM pg_statio_user_tables;

-- Index usage
SELECT 
    schemaname, tablename, indexname,
    idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

## 8. 🚨 Alerting & Notifications

### A. Custom Health Check Script

```bash
#!/bin/bash
# scripts/health_check.sh

# Check API
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  API is DOWN!" | mail -s "Finclator Alert" you@email.com
fi

# Check database
if ! psql finclator -c "SELECT 1" > /dev/null 2>&1; then
    echo "⚠️  Database is DOWN!" | mail -s "Finclator Alert" you@email.com
fi

# Check recent activity
RECENT_TWEETS=$(psql finclator -t -c "SELECT COUNT(*) FROM tweets WHERE ingested_at > NOW() - INTERVAL '1 hour'")
if [ "$RECENT_TWEETS" -eq 0 ]; then
    echo "⚠️  No tweets ingested in last hour!" | mail -s "Finclator Alert" you@email.com
fi
```

### B. Cron Schedule

```bash
# Run health check every 15 minutes
*/15 * * * * /path/to/scripts/health_check.sh
```

---

## 9. 🔐 Security Auditing

### A. Check for Exposed Secrets

```bash
# Search code for potential secrets
grep -r "api_key" --exclude-dir={.venv,.cache}
grep -r "bearer" --exclude-dir={.venv,.cache}
grep -r "password" --exclude-dir={.venv,.cache}
```

### B. Database Access Audit

```sql
-- Check user permissions
SELECT * FROM information_schema.role_table_grants
WHERE grantee = 'your_username';

-- Check active connections
SELECT * FROM pg_stat_activity;
```

---

## 10. 📦 Backup & Recovery

### A. Database Backup

```bash
# Full backup
pg_dump finclator > backup_$(date +%Y%m%d).sql

# Compressed backup
pg_dump finclator | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup specific tables
pg_dump finclator -t tweets -t sentiment_predictions > partial_backup.sql
```

### B. Restore

```bash
# Restore from backup
psql finclator < backup_20251115.sql

# Restore compressed
gunzip -c backup_20251115.sql.gz | psql finclator
```

---

## 11. 🎛️ Recommended Monitoring Stack

### For Production

**Minimal:**
- Admin API endpoints (built-in)
- Application logs
- Basic health checks

**Intermediate:**
- pgAdmin for database inspection
- Jupyter for analysis
- Cron-based health checks

**Advanced:**
- Grafana + Prometheus for metrics
- Sentry for error tracking
- ELK Stack (Elasticsearch, Logstash, Kibana) for logs
- Datadog / New Relic for APM

---

## 12. 📋 Daily Audit Checklist

```bash
# Morning routine
curl http://localhost:8000/admin/stats
curl http://localhost:8000/admin/pipeline-status
tail -n 50 logs/finclator.log | grep ERROR

# Check data quality
psql finclator -c "SELECT COUNT(*) FROM tweets WHERE processed_for_sentiment = FALSE"
psql finclator -c "SELECT asset_symbol, COUNT(*) FROM price_candles WHERE close = 0 GROUP BY asset_symbol"

# Review recent trust scores
curl http://localhost:8000/admin/trust-scores | jq '.[] | select(.computed_at > "2025-11-14")'
```

---

## 13. 🎯 Quick Reference

| Need | Tool | Command |
|------|------|---------|
| Database stats | Admin API | `curl http://localhost:8000/admin/stats` |
| Recent tweets | Admin API | `curl http://localhost:8000/admin/tweets` |
| SQL queries | psql | `psql finclator` |
| Visual DB tool | pgAdmin | Install and connect |
| Export data | Python/pandas | Create export script |
| Monitor logs | tail | `tail -f logs/finclator.log` |
| Health check | curl | `curl http://localhost:8000/health` |
| Performance | EXPLAIN | `EXPLAIN ANALYZE SELECT...` |

---

## 🆘 Troubleshooting

**Issue**: Admin endpoints return 404

**Solution**: Ensure admin router is registered in `src/api/main.py`

**Issue**: Cannot connect to database

**Solution**: Check PostgreSQL is running: `brew services list`

**Issue**: No recent data

**Solution**: Run workers manually to test:
```bash
python -m src.workers.tweet_ingestion
python -m src.workers.sentiment
python -m src.workers.aggregation
```

---

**Created**: 2025-11-15  
**Maintained by**: Finclator Team  
**Status**: Production Ready ✅

