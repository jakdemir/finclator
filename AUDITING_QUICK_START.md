# Finclator Auditing - Quick Start Guide

**🎯 Goal**: View database tables and audit your Finclator system

---

## ✅ What I Just Added

### 1. **Admin API Endpoints** (NEW!)

I created `/admin/*` endpoints to inspect your database via HTTP:

```bash
# Database statistics
curl http://localhost:8000/admin/stats | jq

# Recent tweets (20 latest)
curl http://localhost:8000/admin/tweets | jq

# Recent sentiment predictions
curl http://localhost:8000/admin/predictions | jq

# Price candles for BTC
curl 'http://localhost:8000/admin/price-candles?asset=BTC' | jq

# All trust scores
curl http://localhost:8000/admin/trust-scores | jq

# Prediction outcomes
curl http://localhost:8000/admin/outcomes | jq

# Pipeline status (last 24h activity)
curl http://localhost:8000/admin/pipeline-status | jq
```

**Access via browser**:
- http://localhost:8000/docs - Interactive API docs (test all endpoints)
- http://localhost:8000/admin/stats - Direct JSON response

---

## 🌐 Best Options for Web Interface

### Option 1: Interactive API Docs (Available Now)

**URL**: http://localhost:8000/docs

1. Scroll to "admin" section
2. Click on any endpoint (e.g., `/admin/stats`)
3. Click "Try it out"
4. Click "Execute"
5. See results in browser

**Perfect for**: Quick inspections, testing, sharing with team

---

### Option 2: pgAdmin (Visual Database Tool)

**Install:**
```bash
brew install --cask pgadmin4
```

**Connect:**
1. Open pgAdmin
2. Right-click "Servers" → "Register" → "Server"
3. General tab: Name = "Finclator Local"
4. Connection tab:
   - Host: `localhost`
   - Port: `5432`
   - Database: `finclator`
   - Username: (your postgres user)
5. Save

**Features:**
- ✅ Visual table browser
- ✅ SQL query editor
- ✅ Export to CSV/Excel
- ✅ Data editing
- ✅ Schema diagrams

**Perfect for**: Deep database exploration, complex queries, data exports

---

### Option 3: psql (Command Line)

**Connect:**
```bash
psql finclator
```

**View all tables:**
```sql
\dt
```

**Quick queries:**
```sql
-- Row counts
SELECT 'tweets' AS table, COUNT(*) FROM tweets
UNION ALL SELECT 'predictions', COUNT(*) FROM sentiment_predictions
UNION ALL SELECT 'trust_scores', COUNT(*) FROM trust_scores;

-- Latest tweets
SELECT i.handle, t.text, t.tweeted_at
FROM tweets t
JOIN influencers i ON t.influencer_id = i.id
ORDER BY t.tweeted_at DESC
LIMIT 10;

-- Trust scores
SELECT i.handle, ts.asset_symbol, ts.horizon, ts.score
FROM trust_scores ts
JOIN influencers i ON ts.influencer_id = i.id
ORDER BY ts.score DESC;
```

**Perfect for**: Quick checks, power users, scripting

---

## 📊 Other Excellent Options

### 4. DBeaver (Universal DB Tool)

- **Download**: https://dbeaver.io/download/
- **Free & open source**
- **ER diagrams**
- **Data visualization**
- **Export options**

### 5. Metabase (BI Dashboard)

```bash
docker run -d -p 3000:3000 \
  -e "MB_DB_TYPE=postgres" \
  -e "MB_DB_DBNAME=finclator" \
  -e "MB_DB_PORT=5432" \
  -e "MB_DB_USER=postgres" \
  -e "MB_DB_HOST=host.docker.internal" \
  --name metabase metabase/metabase
```

**Access**: http://localhost:3000

**Features**:
- Drag-and-drop dashboards
- Charts & visualizations  
- Scheduled reports
- Team sharing

### 6. Jupyter Notebook (Data Analysis)

```bash
pip install jupyter pandas matplotlib sqlalchemy

jupyter notebook
```

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('postgresql://localhost/finclator')

# Load any table
df = pd.read_sql("SELECT * FROM tweets", engine)
df.head()

# Analyze
df['asset_symbols'].value_counts()
df.groupby('processed_for_sentiment').size()
```

---

## 🎯 My Recommendation

**For quick checks** (what you asked for):
1. **Start here**: http://localhost:8000/docs 
   - Go to "admin" section
   - Test `/admin/stats`, `/admin/tweets`, etc.
   - No installation needed!

**For deeper analysis**:
2. **Install pgAdmin** (5 minutes)
   - Beautiful visual interface
   - Point-and-click database exploration
   - Perfect for non-technical stakeholders

**For power users**:
3. **Use psql** (already installed)
   - Fast
   - Scriptable
   - Direct SQL access

---

## 🚀 Quick Test

**Right now, try this:**

```bash
# 1. Get database stats
curl -s http://localhost:8000/admin/stats | python -m json.tool

# 2. Get latest 5 tweets
curl -s 'http://localhost:8000/admin/tweets?limit=5' | python -m json.tool

# 3. Get pipeline status
curl -s http://localhost:8000/admin/pipeline-status | python -m json.tool
```

Or **open in browser**:
- http://localhost:8000/docs (then explore admin endpoints)

---

## 📚 Full Documentation

I created comprehensive guides:

1. **`docs/AUDITING_OPTIONS.md`** (13 sections, 400+ lines)
   - All 10+ auditing methods
   - SQL query examples
   - Monitoring scripts
   - Alerting setup
   - Performance profiling

2. **`WEB_INTERFACES.md`**
   - Dashboard guide
   - API documentation
   - Customization tips

---

## 🎨 Future: Enhanced Admin Dashboard

Want me to create a visual admin dashboard HTML page with:
- 📊 Database table viewers
- 📈 Charts and graphs
- 🔍 Search and filter
- 📥 Export buttons
- 🎯 Interactive data exploration

Let me know and I'll build it! 🚀

---

## 🔧 Troubleshooting

**Admin endpoints returning 500 error?**

Restart the server:
```bash
# Kill old server
kill $(cat /tmp/finclator_api.pid 2>/dev/null) 2>/dev/null || pkill -f "uvicorn src.api.main:app"

# Start fresh
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Then test:
```bash
curl http://localhost:8000/admin/stats
```

---

**Database connection issues?**

```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Start if needed
brew services start postgresql
```

---

## ✅ Summary

**You now have multiple ways to audit Finclator:**

| Method | Difficulty | Features | Best For |
|--------|-----------|----------|----------|
| Admin API | ⭐ Easy | HTTP endpoints | Quick checks, team sharing |
| API Docs | ⭐ Easy | Interactive browser | Testing, exploration |
| pgAdmin | ⭐⭐ Medium | Visual GUI | Deep analysis, exports |
| psql | ⭐⭐⭐ Hard | Command line | Power users, scripts |
| Metabase | ⭐⭐ Medium | BI Dashboard | Presentations, monitoring |
| Jupyter | ⭐⭐⭐ Hard | Data science | Analysis, ML, research |

**Start with**: http://localhost:8000/docs → admin section

---

**Created**: 2025-11-15  
**Status**: Ready to use ✅

