# Finclator Web Interfaces Guide

**Last Updated**: 2025-11-15

---

## 🌐 Available Web Interfaces

### 1. **Custom Dashboard** ⭐ (NEW!)

**URL**: http://localhost:8000/dashboard

**Features:**
- 📊 Real-time market signals (BTC, GOLD, SPX)
- 🎯 Visual signal indicators (BUY/NEUTRAL/SELL)
- 📈 Confidence score bars
- 🏫 Finance school breakdowns
- 👥 Tracked influencers list
- 🔄 Auto-refresh every 30 seconds

**What You'll See:**
- **Bitcoin signals** across SHORT, MEDIUM, and LONG horizons
- **Gold signals** (MEDIUM-term)
- **S&P 500 signals** (MEDIUM and LONG-term)
- **Weighted scores** showing BUY/NEUTRAL/SELL confidence percentages
- **School-level breakdown** showing how each finance theory school (Macro, Technical, Value, Growth) views each asset
- **All tracked influencers** with their finance school affiliations

**Perfect For:**
- Quick overview of current market sentiment
- Monitoring system status
- Presenting to stakeholders
- Daily decision-making

---

### 2. **Interactive API Documentation (Swagger UI)**

**URL**: http://localhost:8000/docs

**Features:**
- 📝 Complete API documentation
- 🧪 Test endpoints directly in browser
- 📋 Request/response examples
- 🔍 Schema definitions

**Available Endpoints:**
```
GET  /                        - Health check
GET  /health                  - Detailed health status
GET  /signals                 - Get overall signal
     ?asset=BTC&horizon=SHORT
GET  /signals/school-signals  - Get per-school signals
     ?asset=BTC&horizon=MEDIUM
GET  /influencers             - List all influencers
GET  /influencers/{id}        - Get influencer details
```

**Perfect For:**
- Testing API endpoints
- Understanding API structure
- Development and debugging
- Integration planning

---

### 3. **Alternative API Documentation (ReDoc)**

**URL**: http://localhost:8000/redoc

**Features:**
- 📖 Clean, readable documentation
- 📚 Better for learning
- 🎨 Beautiful design
- 📱 Mobile-friendly

**Perfect For:**
- Reading API documentation
- Sharing with team members
- Learning the API structure

---

## 🚀 Quick Start

### Start the Server

```bash
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Access Interfaces

1. **Dashboard**: Open http://localhost:8000/dashboard in your browser
2. **API Docs**: Open http://localhost:8000/docs
3. **ReDoc**: Open http://localhost:8000/redoc

---

## 📊 Dashboard Usage

### Interpreting Signals

**Signal Labels:**
- 🟢 **BUY**: Weighted score > 50% buy sentiment
- 🟡 **NEUTRAL**: No clear direction
- 🔴 **SELL**: Weighted score > 50% sell sentiment

**Score Bars:**
- **Green**: Buy sentiment strength
- **Orange**: Neutral sentiment
- **Red**: Sell sentiment strength

**School Breakdown:**
Shows how each finance theory approaches the market:
- **Macro**: Focus on economic indicators
- **Technical**: Chart patterns and price action
- **Value**: Fundamental analysis
- **Growth**: Future potential

### Refresh Data

- **Automatic**: Dashboard auto-refreshes every 30 seconds
- **Manual**: Click the "🔄 Refresh Data" button

---

## 🔧 Customization

### Update Dashboard Colors

Edit `src/api/static/dashboard.html` and modify the CSS variables:

```css
.label-buy { color: #10b981; }     /* Green */
.label-sell { color: #ef4444; }     /* Red */
.label-neutral { color: #f59e0b; }  /* Orange */
```

### Add More Signal Cards

In `dashboard.html`, add new cards:

```html
<div class="card signal-card" id="new-signal-card">
    <h2>🆕 New Asset (Horizon)</h2>
    <div id="new-signal-content" class="loading">Loading...</div>
</div>
```

Then update the JavaScript:

```javascript
loadSignal('ASSET', 'HORIZON', 'new-signal-content', 'new-signal-card')
```

---

## 📱 Access from Other Devices

### Same Network

1. Find your local IP:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. Start server on all interfaces:
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

3. Access from other devices:
   ```
   http://YOUR_IP:8000/dashboard
   ```

### Production (Render)

Once deployed to Render:
```
https://finclator-api.onrender.com/dashboard
```

---

## 🛠️ Troubleshooting

### Dashboard Not Loading

**Issue**: Blank page or 404 error

**Solution**:
```bash
# Verify static directory exists
ls src/api/static/dashboard.html

# Restart server
pkill -f "uvicorn src.api.main:app"
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### No Data Showing

**Issue**: "Signal not available" messages

**Solution**: Run the aggregation worker:
```bash
python -m src.workers.aggregation
```

### CORS Errors

**Issue**: Cannot access from different origin

**Solution**: CORS is already configured to allow all origins. If issues persist, check browser console for specific errors.

---

## 📸 Screenshots

### Dashboard Overview
- Real-time signal cards with color-coded indicators
- Confidence score visualizations
- School-level breakdowns
- Influencer list with finance school tags

### Signal Card Details
Each card shows:
- 🎯 Signal label (BUY/NEUTRAL/SELL)
- 📊 Three confidence bars (BUY/NEUTRAL/SELL percentages)
- 🏫 Finance school breakdown
- ⏰ Last updated timestamp

---

## 🔮 Future Enhancements

Potential additions:
- 📈 Historical signal charts
- 🎯 Trust score visualizations
- 📊 Influencer performance leaderboard
- 💬 Recent tweets display
- ⚡ Live WebSocket updates
- 📱 Mobile app

---

## 🎯 API Endpoint Examples

### Get Signal via curl

```bash
# Overall BTC MEDIUM signal
curl 'http://localhost:8000/signals?asset=BTC&horizon=MEDIUM' | jq

# School breakdown for GOLD
curl 'http://localhost:8000/signals/school-signals?asset=GOLD&horizon=MEDIUM' | jq

# List all influencers
curl 'http://localhost:8000/influencers' | jq

# Get specific influencer (Sant Manukyan)
curl 'http://localhost:8000/influencers/8f3d9c5b-67ef-4dad-8982-dd2eceef2c31' | jq
```

### Response Examples

**Signal Response:**
```json
{
  "asset": "BTC",
  "horizon": "MEDIUM",
  "final_label": "BUY",
  "weighted_score_buy": 0.521,
  "weighted_score_neutral": 0.479,
  "weighted_score_sell": 0.0,
  "generated_at": "2025-11-15T16:54:08"
}
```

**School Signals Response:**
```json
[
  {
    "finance_school": "Macro",
    "asset": "BTC",
    "horizon": "MEDIUM",
    "final_label": "NEUTRAL",
    "weighted_score_buy": 0.0,
    "weighted_score_neutral": 1.0,
    "weighted_score_sell": 0.0,
    "generated_at": "2025-11-15T16:54:08"
  },
  {
    "finance_school": "Value",
    "asset": "BTC",
    "horizon": "MEDIUM",
    "final_label": "BUY",
    "weighted_score_buy": 1.0,
    "weighted_score_neutral": 0.0,
    "weighted_score_sell": 0.0,
    "generated_at": "2025-11-15T16:54:08"
  }
]
```

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Project README**: `/README.md`
- **Operations Guide**: `/docs/OPERATIONS.md`
- **Deployment Guide**: `/DEPLOYMENT_READY.txt`

---

## 🆘 Support

For issues or questions:
1. Check logs: `tail -f logs/finclator.log`
2. Verify API is running: `curl http://localhost:8000/health`
3. Run validation: `python scripts/validate_mvp.py`
4. Review documentation: `/docs/`

---

**Created**: 2025-11-15  
**Version**: 1.0.0  
**Status**: Production Ready ✅

