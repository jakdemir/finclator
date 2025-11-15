# 🧭 Finclator Navigation Guide

**Seamless navigation between all interfaces** — Every page includes a consistent navigation bar for easy access.

---

## 🎯 Navigation Bar (Available on All Pages)

Every Finclator interface includes this navigation bar at the top:

```
🎯 Finclator    |    📊 Dashboard    ⚙️ Admin    📖 API Docs    ❤️ Health
```

**Click any link to instantly switch between interfaces** — No need to manually type URLs!

---

## 🌐 Interface Overview

### 1. 📊 User Dashboard
**URL**: http://localhost:8000/dashboard

**Purpose**: Quick market signal overview

**Features**:
- Real-time BUY/NEUTRAL/SELL signals
- Confidence scores with visual progress bars
- Finance school breakdowns (Macro, Technical, Value, Growth)
- Tracked influencers list
- Auto-refresh every 30 seconds

**Best For**:
- Quick decision making
- Market overview at a glance
- Monitoring signal changes
- Public-facing view (no sensitive data)

**Navigation**: Click any link in the top bar to switch to another interface

---

### 2. ⚙️ Admin Dashboard
**URL**: http://localhost:8000/admin

**Purpose**: Comprehensive database management and monitoring

**Features** (7 Tabs):

#### 📊 Overview
- Database statistics
- Data distribution charts
- Sentiment pie chart
- Tweets by asset bar chart

#### 💬 Tweets
- All collected tweets
- Search, filter, export to CSV
- Influencer details
- Processing status

#### 🎯 Predictions
- Sentiment classifications
- Confidence scores
- Filter by asset/direction
- Export functionality

#### 💹 Prices
- OHLCV data tables
- Interactive price charts
- Filter by asset
- Historical data view

#### 🏆 Trust Scores
- Influencer performance metrics
- Score distribution charts
- Search by influencer
- Real-time calculations

#### ✅ Outcomes
- Prediction evaluation results
- Return percentages
- Entry/exit prices
- Correct/Wrong/Unclear status

#### 📈 Monitoring
- Real-time pipeline status
- 24-hour activity metrics
- Latest activity log
- Activity timeline charts

**Best For**:
- System troubleshooting
- Data quality checks
- Performance monitoring
- Database auditing
- Export/analysis

**Navigation**: Top bar for main navigation + tab bar for sections

---

### 3. 📖 API Documentation
**URL**: http://localhost:8000/docs

**Purpose**: Interactive API testing and documentation

**Features**:
- All endpoints documented
- Try API calls directly in browser
- See request/response schemas
- Authorization testing
- Download OpenAPI spec

**Available Endpoints**:
- `/signals` - Get overall market signals
- `/signals/school-signals` - Get school-specific signals
- `/influencers` - List all influencers
- `/influencers/{id}` - Get influencer details
- `/admin/*` - Admin API endpoints

**Best For**:
- API integration
- Development
- Testing queries
- Understanding data models
- Building custom clients

**Navigation**: Click dashboard or admin links to return to UI

---

### 4. ❤️ Health Check
**URL**: http://localhost:8000/health

**Purpose**: Quick system status check

**Response**:
```json
{
  "status": "ok",
  "database": "connected"
}
```

**Best For**:
- Uptime monitoring
- Deployment verification
- Automated health checks

**Navigation**: Opens in new tab (doesn't disrupt workflow)

---

## 🔄 Navigation Flow Examples

### Common Workflows

#### Workflow 1: Check Signals → Investigate Data
1. Start at **Dashboard** (view signals)
2. Click **⚙️ Admin** in nav bar
3. Go to **💬 Tweets** tab (see source data)
4. Switch to **🎯 Predictions** tab (see sentiment)
5. Check **🏆 Trust Scores** (verify influencer performance)

#### Workflow 2: Monitor System → Test API
1. Start at **Admin Dashboard**
2. Go to **📈 Monitoring** tab (check pipeline status)
3. Click **📖 API Docs** in nav bar
4. Test `/admin/stats` endpoint
5. Click **⚙️ Admin** to return to dashboard

#### Workflow 3: Development → Verification
1. Start at **API Docs** (test new endpoint)
2. Click **⚙️ Admin** in nav bar
3. Go to **📊 Overview** tab (verify data updated)
4. Click **📊 Dashboard** in nav bar
5. Confirm signals updated correctly

---

## 🎨 Visual Navigation Map

```
┌─────────────────────────────────────────────────────────────┐
│  🎯 Finclator  |  📊 Dashboard  ⚙️ Admin  📖 Docs  ❤️ Health │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │   📊 User   │────▶│  ⚙️ Admin    │────▶│  📖 API     │  │
│  │  Dashboard  │     │   Dashboard  │     │    Docs     │  │
│  └─────────────┘     └──────────────┘     └─────────────┘  │
│        │                     │                     │         │
│        │                     │                     │         │
│        └─────────────────────┴─────────────────────┘         │
│                              │                               │
│                       ┌──────▼──────┐                        │
│                       │  ❤️ Health  │                        │
│                       │    Check    │                        │
│                       └─────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

**Every interface connects to every other interface** — One click away!

---

## 🚀 Quick Access Tips

### Keyboard Shortcuts
While Finclator doesn't have built-in keyboard shortcuts, you can use browser shortcuts:

- **Cmd/Ctrl + L**: Focus address bar (type new URL)
- **Cmd/Ctrl + R**: Refresh current page
- **Cmd/Ctrl + T**: New tab (open multiple interfaces)
- **Cmd/Ctrl + W**: Close current tab

### Browser Bookmarks
Save these bookmarks for instant access:

```
📌 Finclator Dashboard → http://localhost:8000/dashboard
📌 Finclator Admin    → http://localhost:8000/admin
📌 Finclator API Docs → http://localhost:8000/docs
📌 Finclator Health   → http://localhost:8000/health
```

### Multiple Monitor Setup
Open different interfaces side-by-side:

**Monitor 1**: Admin Dashboard (monitoring)  
**Monitor 2**: User Dashboard (signals)  
**Monitor 3**: Terminal (logs)

### Tab Management
Recommended tab layout:

```
Tab 1: Dashboard (auto-refresh)
Tab 2: Admin (data inspection)
Tab 3: API Docs (testing)
Tab 4: Terminal (server logs)
```

---

## 🔧 Troubleshooting Navigation

### Issue: Navigation Links Not Working

**Symptoms**: Clicking nav links returns 404 or doesn't navigate

**Solutions**:
1. Check server is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Restart server:
   ```bash
   pkill -f "uvicorn src.api.main:app"
   cd /Users/jakdemir/projects/finclator
   source .venv/bin/activate
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

3. Clear browser cache (Cmd/Ctrl + Shift + R)

### Issue: Wrong Interface Showing

**Symptoms**: URL shows `/admin` but you see dashboard

**Solution**: Hard refresh (Cmd/Ctrl + Shift + R)

### Issue: Navigation Bar Missing

**Symptoms**: No navigation bar visible at top of page

**Solutions**:
1. Ensure you're on latest version (refresh page)
2. Check browser console for JavaScript errors
3. Restart server to reload HTML files

---

## 🎯 Navigation Best Practices

### ✅ DO:
- Use navigation bar for quick switching
- Keep multiple tabs open for parallel workflows
- Bookmark frequently used interfaces
- Use Health check to verify system before troubleshooting

### ❌ DON'T:
- Don't rely only on back button (use nav bar instead)
- Don't manually type URLs (use nav links)
- Don't forget to check Health if interfaces seem unresponsive
- Don't close all tabs (keep at least Dashboard open)

---

## 📱 Mobile/Tablet Access

### Same Network Access

1. **Find your IP**:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. **Access from mobile device**:
   ```
   http://YOUR_IP:8000/dashboard
   http://YOUR_IP:8000/admin
   http://YOUR_IP:8000/docs
   ```

3. **Navigation works the same** — tap any nav link to switch

### Responsive Design
- Dashboard: ✅ Mobile-friendly
- Admin: ⚠️ Best on tablet/desktop (tables need horizontal space)
- API Docs: ✅ Mobile-friendly

---

## 🔗 External Integration

### Embedding in Other Tools

**Option 1: iFrame** (not recommended for security)
```html
<iframe src="http://localhost:8000/dashboard" width="100%" height="600"></iframe>
```

**Option 2: Link from Other Apps**
```html
<a href="http://localhost:8000/dashboard" target="_blank">View Finclator Signals</a>
```

**Option 3: API Integration** (recommended)
```python
import requests
response = requests.get('http://localhost:8000/signals?asset=BTC&horizon=MEDIUM')
signals = response.json()
```

---

## 📚 Related Documentation

- **QUICK_ACCESS.md** — Quick reference for all interfaces
- **DASHBOARDS_GUIDE.md** — Detailed dashboard features
- **AUDITING_OPTIONS.md** — 10+ ways to inspect data
- **WEB_INTERFACES.md** — Technical implementation details

---

## 🎉 Summary

**🎯 One Navigation Bar. Four Interfaces. Zero Friction.**

Every Finclator interface includes the same navigation bar:
- Click any link to instantly switch
- No manual URL typing needed
- Consistent experience across all pages
- Mobile-friendly on all interfaces

**Current Status**: ✅ All navigation operational

**Server**: http://localhost:8000

**Last Updated**: 2025-11-15

---

**Pro Tip**: Keep the Admin Dashboard and User Dashboard open in separate tabs for the ultimate Finclator experience! 🚀

