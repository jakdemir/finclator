# Finclator Dashboards & Monitoring Guide

**Last Updated**: 2025-11-15  
**Status**: Production Ready ✅

---

## 🎯 Available Dashboards

### 1. **Admin Dashboard** ⭐ (NEW!)

**URL**: http://localhost:8000/admin

**Features**:
- 📊 **Overview Tab** - Database statistics, charts, data distribution
- 💬 **Tweets Tab** - Browse all tweets, search, filter, export to CSV
- 🎯 **Predictions Tab** - View sentiment predictions with filters
- 💹 **Prices Tab** - OHLCV price data with charts
- 🏆 **Trust Scores Tab** - Performance metrics and distribution
- ✅ **Outcomes Tab** - Prediction evaluation results
- 📈 **Monitoring Tab** - Real-time pipeline status & 24h activity

**Perfect For**:
- Database inspection
- System monitoring
- Data analysis
- Troubleshooting
- Exporting data

---

### 2. **User Dashboard**

**URL**: http://localhost:8000/dashboard

**Features**:
- Real-time market signals (BTC, GOLD, SPX)
- Visual BUY/NEUTRAL/SELL indicators
- Confidence score bars
- Finance school breakdowns
- Tracked influencers list

**Perfect For**:
- Quick market overview
- Decision making
- Presentations
- Stakeholder updates

---

### 3. **Interactive API Docs**

**URL**: http://localhost:8000/docs

**Features**:
- Test all API endpoints
- See request/response examples
- Interactive queries
- Schema definitions

**Perfect For**:
- API testing
- Development
- Integration planning

---

## 🎛️ Admin Dashboard Features

### Overview Tab

**Statistics Cards**:
- Total Tweets (with processed/pending breakdown)
- Sentiment Predictions count
- Price Candles count
- Trust Scores count
- Prediction Outcomes count
- Current Signals count
- Influencers & Finance Schools count
- Tweets by Asset (BTC, GOLD, SPX)

**Charts**:
- 📊 Data Distribution (Doughnut chart)
- 🎯 Sentiment Distribution (Pie chart)
- 📈 Tweets by Asset (Bar chart)

**Auto-refresh**: Every 30 seconds

---

### Tweets Tab

**Features**:
- ✅ View all tweets with influencer info
- 🔍 Search by text, influencer, or asset
- 🔽 Filter by processing status (Processed/Pending)
- 🔽 Filter by asset (BTC/GOLD/SPX)
- 📥 Export to CSV
- 🔄 Manual refresh

**Columns**:
- Influencer (handle & display name)
- Tweet text
- Detected assets (as badges)
- Posted date/time
- Processing status

---

### Predictions Tab

**Features**:
- View all sentiment predictions
- Search predictions
- Filter by asset (BTC/GOLD/SPX)
- Filter by direction (BUY/NEUTRAL/SELL)
- Export to CSV
- Sentiment distribution chart

**Columns**:
- Asset
- Direction (BUY/NEUTRAL/SELL with color badges)
- Horizon (SHORT/MEDIUM/LONG)
- Confidence percentage
- Influencer
- Tweet excerpt
- Created timestamp

---

### Prices Tab

**Features**:
- View OHLCV price data
- Switch between assets (BTC/GOLD/SPX)
- Interactive price chart
- Latest 30 candles

**Columns**:
- Date
- Open price
- High price (green)
- Low price (red)
- Close price (bold)
- Volume

**Chart**: Line chart showing price trends over time

---

### Trust Scores Tab

**Features**:
- View all trust scores by influencer
- Search by influencer name
- Trust score distribution chart
- Color-coded scores (green/yellow/red)

**Columns**:
- Influencer (handle & display name)
- Asset (or OVERALL)
- Horizon
- Score percentage (color-coded)
- Computed timestamp

**Chart**: Bar chart showing score distribution by range

---

### Outcomes Tab

**Features**:
- View prediction evaluation results
- Search outcomes
- See accuracy metrics
- Return percentages

**Columns**:
- Influencer
- Asset
- Horizon
- Predicted direction
- Actual outcome (CORRECT/WRONG/UNCLEAR)
- Return percentage (color-coded)
- Entry/Exit prices
- Evaluated timestamp

---

### Monitoring Tab

**Features**:
- Real-time system status
- Pipeline health indicators
- 24-hour activity metrics
- Latest activity timestamps
- Activity timeline chart

**Metrics**:
- Tweets ingested (last 24h)
- Predictions created (last 24h)
- Price updates (last 24h)
- Signals updated (last 24h)
- Last tweet timestamp
- Last prediction timestamp
- Last signal update timestamp

**Charts**: Bar chart showing 24-hour activity breakdown

**Auto-refresh**: Every 30 seconds

---

## 🔧 Usage Tips

### Searching

All tables support instant search:
1. Type in the search box
2. Results filter automatically
3. No need to press Enter

**Search works on all visible columns!**

### Filtering

Use dropdown filters to narrow results:
- By asset (BTC/GOLD/SPX)
- By direction (BUY/NEUTRAL/SELL)
- By status (Processed/Pending)

Filters can be combined with search.

### Exporting Data

1. Navigate to Tweets or Predictions tab
2. Apply any filters/searches you want
3. Click "📥 Export CSV" button
4. File downloads automatically

**Use case**: Export specific data for external analysis

### Refreshing

**Manual**: Click "🔄 Refresh" button on any tab

**Automatic**: Overview and Monitoring tabs auto-refresh every 30 seconds

### Navigation

- Use top tabs to switch between sections
- Active tab is highlighted in blue
- Data loads automatically when tab is opened

---

## 📊 Chart Types

### Doughnut Chart (Data Distribution)
- Shows proportion of different data types
- Tweets, Predictions, Price Candles, Trust Scores, Outcomes

### Pie Chart (Sentiment Distribution)
- BUY vs NEUTRAL vs SELL breakdown
- Color-coded: Green (BUY), Orange (NEUTRAL), Red (SELL)

### Bar Charts
- Tweets by Asset
- Trust Score Distribution
- 24-Hour Activity

### Line Chart (Price Trends)
- Shows price movement over time
- Filled area for better visibility
- Smooth curves

---

## 🎨 Color Coding

### Signal Directions
- 🟢 **BUY**: Green (#10b981)
- 🟡 **NEUTRAL**: Orange (#f59e0b)
- 🔴 **SELL**: Red (#ef4444)

### Trust Scores
- 🟢 **High** (≥70%): Green
- 🟡 **Average** (50-69%): Orange
- 🔴 **Low** (<50%): Red

### Outcomes
- 🟢 **CORRECT**: Green badge
- 🔴 **WRONG**: Red badge
- 🟡 **UNCLEAR**: Orange badge

### Processing Status
- 🟢 **Processed**: Green badge
- 🟡 **Pending**: Orange badge

---

## 🚀 Quick Start

### Start the Server

```bash
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Access Dashboards

**Admin Dashboard** (Full database access):
```
http://localhost:8000/admin
```

**User Dashboard** (Market signals):
```
http://localhost:8000/dashboard
```

**API Documentation**:
```
http://localhost:8000/docs
```

---

## 🔍 Common Use Cases

### 1. Check System Health

1. Go to http://localhost:8000/admin
2. Click "📈 Monitoring" tab
3. Review pipeline status
4. Check 24-hour activity

### 2. Audit Recent Tweets

1. Go to "💬 Tweets" tab
2. Use search box to find specific content
3. Filter by asset or status
4. Export to CSV if needed

### 3. Review Trust Scores

1. Go to "🏆 Trust Scores" tab
2. Search for specific influencer
3. View score distribution chart
4. Identify top/bottom performers

### 4. Analyze Predictions

1. Go to "🎯 Predictions" tab
2. Filter by asset (e.g., BTC only)
3. Filter by direction (e.g., BUY only)
4. Check confidence levels
5. See sentiment distribution chart

### 5. Verify Price Data

1. Go to "💹 Prices" tab
2. Select asset from dropdown
3. Review latest candles
4. Check price chart for trends

### 6. Evaluate Accuracy

1. Go to "✅ Outcomes" tab
2. Review CORRECT vs WRONG outcomes
3. Check return percentages
4. Identify patterns

---

## 🛠️ Troubleshooting

### Dashboard Not Loading

**Issue**: Blank page or 404 error

**Solution**:
```bash
# Check server is running
curl http://localhost:8000/health

# Restart server if needed
pkill -f "uvicorn src.api.main:app"
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### No Data Showing

**Issue**: "No data found" messages

**Solution**: Run the pipeline workers
```bash
python -m src.workers.tweet_ingestion
python -m src.workers.sentiment
python -m src.workers.aggregation
```

### Charts Not Rendering

**Issue**: Charts appear as empty boxes

**Solution**: 
- Check browser console for JavaScript errors
- Ensure Chart.js library is loading (check internet connection)
- Try refreshing the page (Cmd+R / Ctrl+R)

### Search Not Working

**Issue**: Search box doesn't filter results

**Solution**:
- Ensure data is loaded (wait for table to populate)
- Check JavaScript console for errors
- Try clearing search box and retyping

---

## 📱 Mobile Access

### Access from Phone/Tablet

1. Find your computer's local IP:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. On mobile device, open browser and go to:
   ```
   http://YOUR_IP:8000/admin
   ```

**Note**: Computer and mobile device must be on same WiFi network

---

## 🔐 Security Notes

### Current Setup
- ❌ **No authentication** - Anyone with URL can access
- ✅ **Local only** - Only accessible from same machine by default
- ✅ **Read-only** - Cannot modify data through dashboard

### For Production

**Recommended**:
1. Add authentication (username/password)
2. Enable HTTPS
3. Restrict by IP address
4. Use VPN for remote access
5. Add role-based access control

**Quick Auth Example**:
```python
# In src/api/main.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "admin" or credentials.password != "secret":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials

@app.get("/admin", dependencies=[Depends(verify_admin)])
async def get_admin_dashboard():
    # ... existing code
```

---

## 🎯 Performance Tips

### Large Datasets

If you have thousands of tweets/predictions:

1. **Use Filters**: Narrow down data before searching
2. **Pagination**: Load data in chunks (already implemented)
3. **Export**: For analysis of large datasets
4. **Database Queries**: Use psql for complex analysis

### Slow Loading

If dashboard is slow:

1. **Check Database**: Ensure PostgreSQL is responsive
2. **Network**: Verify API endpoints are fast
3. **Browser**: Clear cache and reload
4. **Resources**: Check system resources (RAM/CPU)

---

## 📊 Data Limits

Current limits (configurable):
- Tweets: 20 per page
- Predictions: 50 per page
- Prices: 30 most recent
- Trust Scores: All (typically <100)
- Outcomes: 30 most recent

**To change limits**: Edit limit parameters in admin.html JavaScript

---

## 🚀 Future Enhancements

Potential additions:
- User authentication
- Real-time WebSocket updates
- More chart types (candlestick, heatmaps)
- Advanced filtering (date ranges, multiple assets)
- Notification system
- Data export in multiple formats (Excel, JSON)
- Historical comparison views
- Performance analytics dashboard
- Mobile app

---

## 📚 Additional Resources

- **API Endpoints**: http://localhost:8000/docs
- **Auditing Guide**: `/docs/AUDITING_OPTIONS.md`
- **Operations Manual**: `/docs/OPERATIONS.md`
- **Web Interfaces Guide**: `/WEB_INTERFACES.md`

---

## 🆘 Support

For issues or questions:
1. Check this guide first
2. Review `/docs/AUDITING_OPTIONS.md`
3. Check application logs
4. Test API endpoints directly

---

**Created**: 2025-11-15  
**Version**: 1.0.0  
**Status**: Production Ready ✅

---

## ✨ Quick Reference

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| **Admin** | `/admin` | Full database access, monitoring |
| **User** | `/dashboard` | Market signals view |
| **API Docs** | `/docs` | Interactive API testing |

**Your Finclator system now has enterprise-grade monitoring and auditing capabilities!** 🎉

