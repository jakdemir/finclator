# 🚀 Finclator Quick Access Guide

**Server Status**: ✅ Running on http://localhost:8000

---

## 🧭 NAVIGATION MADE EASY

**Every interface now includes a navigation bar** — No more manually typing URLs!

```
┌──────────────────────────────────────────────────────────┐
│  🎯 Finclator  |  📊 Dashboard  ⚙️ Admin  📖 Docs  ❤️    │
└──────────────────────────────────────────────────────────┘
```

**Click any link to instantly switch between interfaces** ⚡

📖 **See full navigation guide**: `NAVIGATION_GUIDE.md`

---

## 🌐 All Available Interfaces

| Interface | URL | Status | Purpose |
|-----------|-----|--------|---------|
| **Admin Dashboard** ⭐ | http://localhost:8000/admin | ✅ Working | Full database & monitoring |
| **User Dashboard** | http://localhost:8000/dashboard | ✅ Working | Market signals |
| **API Documentation** | http://localhost:8000/docs | ✅ Working | Interactive API testing |
| **Health Check** | http://localhost:8000/health | ✅ Working | System status |

---

## 🎯 Quick Start

### 1. Admin Dashboard (Most Powerful)

**Open**: http://localhost:8000/admin

**Features**:
- 📊 **Overview** - Database statistics & charts
- 💬 **Tweets** - Browse, search, filter, export
- 🎯 **Predictions** - Sentiment analysis results
- 💹 **Prices** - OHLCV data with charts
- 🏆 **Trust Scores** - Performance metrics
- ✅ **Outcomes** - Prediction accuracy
- 📈 **Monitoring** - Real-time pipeline status

**Use this for**: Database inspection, troubleshooting, data analysis

---

### 2. User Dashboard (Signal Viewer)

**Open**: http://localhost:8000/dashboard

**Features**:
- Real-time market signals
- BUY/NEUTRAL/SELL indicators
- Confidence scores
- Finance school breakdowns

**Use this for**: Quick market overview, decision making

---

### 3. API Documentation (Developer Tool)

**Open**: http://localhost:8000/docs

**Features**:
- Interactive API testing
- All endpoints documented
- Try queries in browser
- See response schemas

**Use this for**: API integration, development, testing

---

## 📊 Working Endpoints

### Core API
```bash
# Health check
curl http://localhost:8000/health

# Overall signal
curl 'http://localhost:8000/signals?asset=BTC&horizon=MEDIUM'

# School signals
curl 'http://localhost:8000/signals/school-signals?asset=BTC&horizon=MEDIUM'

# List influencers
curl http://localhost:8000/influencers

# Get specific influencer
curl http://localhost:8000/influencers/8f3d9c5b-67ef-4dad-8982-dd2eceef2c31
```

### OpenAPI Spec
```bash
# Get API specification
curl http://localhost:8000/openapi.json
```

---

## 🔧 Server Management

### Check if Server is Running
```bash
curl http://localhost:8000/health
```

**Expected**: `{"status":"ok","database":"connected"}`

### Start Server
```bash
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Stop Server
```bash
# Kill by PID
kill $(cat /tmp/finclator_api.pid)

# Or kill all
pkill -f "uvicorn src.api.main:app"
```

### Restart Server
```bash
pkill -f "uvicorn src.api.main:app"
sleep 2
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
```

---

## 📚 Documentation

| Guide | File | Purpose |
|-------|------|---------|
| **Dashboards** | `DASHBOARDS_GUIDE.md` | Complete dashboard manual |
| **Auditing** | `docs/AUDITING_OPTIONS.md` | 10+ auditing methods |
| **Operations** | `docs/OPERATIONS.md` | Production runbook |
| **API Caching** | `docs/API_CACHING.md` | Caching strategy |
| **Deployment** | `DEPLOYMENT_READY.txt` | Production deployment |
| **Validation** | `PRE_DEPLOYMENT_VALIDATION.md` | Full system validation |

---

## 🎯 Common Tasks

### View Database Tables
1. Open http://localhost:8000/admin
2. Click on any tab (Tweets, Predictions, etc.)
3. Use search/filter as needed

### Check System Health
1. Open http://localhost:8000/admin
2. Click "📈 Monitoring" tab
3. Review 24-hour activity

### Get Market Signals
1. Open http://localhost:8000/dashboard
2. View all signals with confidence scores
3. Check school breakdowns

### Export Data
1. Go to http://localhost:8000/admin
2. Open Tweets or Predictions tab
3. Apply filters if needed
4. Click "📥 Export CSV"

### Test API
1. Open http://localhost:8000/docs
2. Expand any endpoint
3. Click "Try it out"
4. Click "Execute"

---

## 🛠️ Troubleshooting

### Dashboard Not Loading

**Check server**:
```bash
curl http://localhost:8000/health
```

**Restart if needed**:
```bash
pkill -f "uvicorn src.api.main:app"
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### No Data Showing

**Run workers**:
```bash
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate

# Ingest tweets
python -m src.workers.tweet_ingestion

# Classify sentiment
python -m src.workers.sentiment

# Aggregate signals
python -m src.workers.aggregation
```

### Database Issues

**Check PostgreSQL**:
```bash
brew services list | grep postgresql
```

**Connect manually**:
```bash
psql finclator
```

---

## 🌐 Access from Other Devices

### Same Network

1. Find your IP:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. Access from other device:
   ```
   http://YOUR_IP:8000/admin
   http://YOUR_IP:8000/dashboard
   ```

---

## 🎉 Quick Wins

### 5-Second Health Check
```bash
curl http://localhost:8000/health && echo " ✅"
```

### 10-Second Data Overview
Open: http://localhost:8000/admin

### 30-Second Signal Check
Open: http://localhost:8000/dashboard

### 1-Minute Database Audit
1. Open: http://localhost:8000/admin
2. Check Overview stats
3. Done!

---

## 🔗 External Tools

### Visual Database Tools

**pgAdmin** (Best for SQL):
```bash
brew install --cask pgadmin4
```
Then connect to `localhost:5432/finclator`

**DBeaver** (Universal):
Download from https://dbeaver.io/download/

### Command Line

**psql** (SQL queries):
```bash
psql finclator
```

**Python script** (Custom queries):
```bash
python scripts/validate_mvp.py
```

---

## 📞 Quick Reference

**Need to...**
- **View database?** → http://localhost:8000/admin
- **Check signals?** → http://localhost:8000/dashboard
- **Test API?** → http://localhost:8000/docs
- **Monitor system?** → http://localhost:8000/admin → Monitoring tab
- **Export data?** → http://localhost:8000/admin → Tweets/Predictions tab → Export CSV
- **See trust scores?** → http://localhost:8000/admin → Trust Scores tab

---

## ✅ Verification Checklist

Before using, verify:
- [ ] Server running: `curl http://localhost:8000/health`
- [ ] Admin dashboard loads: http://localhost:8000/admin
- [ ] User dashboard loads: http://localhost:8000/dashboard
- [ ] API docs accessible: http://localhost:8000/docs
- [ ] Database has data (check Overview tab)

---

## 🆘 Need Help?

1. **Check documentation**: See files listed above
2. **View logs**: Check terminal output where server is running
3. **Restart server**: `pkill -f uvicorn` then restart
4. **Run workers**: Ensure pipeline has processed data
5. **Check database**: `psql finclator` to verify data exists

---

**Last Updated**: 2025-11-15  
**Server**: http://localhost:8000  
**Status**: ✅ Operational

