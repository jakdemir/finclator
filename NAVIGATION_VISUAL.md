# 🎯 Finclator Navigation — Visual Reference

**Quick visual guide to navigating all Finclator interfaces**

---

## 🧭 Navigation Bar (On Every Page)

```
╔════════════════════════════════════════════════════════════════╗
║  🎯 Finclator  │  📊 Dashboard  ⚙️ Admin  📖 API Docs  ❤️      ║
╚════════════════════════════════════════════════════════════════╝
```

**Always visible at the top** — Click any link to switch instantly!

---

## 🌐 Interface Flow Diagram

```
                    ┌─────────────────────────┐
                    │   🎯 Finclator System   │
                    └───────────┬─────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
    ┌───────────▼───────┐  ┌───▼───────┐  ┌───▼────────┐
    │  📊 Dashboard    │  │ ⚙️ Admin   │  │ 📖 Docs    │
    │                   │  │            │  │            │
    │  • Market Signals │  │  • Tables  │  │  • API Test│
    │  • Schools        │  │  • Charts  │  │  • Schemas │
    │  • Auto-refresh   │  │  • Export  │  │  • OpenAPI │
    └───────────────────┘  └────────────┘  └────────────┘
                                │
                         ┌──────┴──────┐
                         │  ❤️ Health  │
                         │  Check      │
                         └─────────────┘
```

**All interfaces connected** — Navigate freely in any direction!

---

## 📊 Dashboard Interface Map

```
╔═══════════════════════════════════════════════════════════╗
║ 🎯 Finclator │ 📊 Dashboard ⚙️ Admin 📖 Docs ❤️          ║
╠═══════════════════════════════════════════════════════════╣
║                                                             ║
║  🎯 Finclator Dashboard                                    ║
║  Trust-scored market indicators from influencer sentiment  ║
║                                                             ║
║  ● System Online        [🔄 Refresh Data]                  ║
║                                                             ║
╠═══════════════════════════════════════════════════════════╣
║                                                             ║
║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       ║
║  │  ₿ Bitcoin  │  │  ₿ Bitcoin  │  │  ₿ Bitcoin  │       ║
║  │  SHORT-term │  │ MEDIUM-term │  │  LONG-term  │       ║
║  │             │  │             │  │             │       ║
║  │   [BUY]     │  │  [NEUTRAL]  │  │   [SELL]    │       ║
║  │   85%       │  │    60%      │  │    40%      │       ║
║  └─────────────┘  └─────────────┘  └─────────────┘       ║
║                                                             ║
║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       ║
║  │  🏆 Gold    │  │  📈 S&P 500 │  │  📈 S&P 500 │       ║
║  │ MEDIUM-term │  │ MEDIUM-term │  │  LONG-term  │       ║
║  └─────────────┘  └─────────────┘  └─────────────┘       ║
║                                                             ║
╠═══════════════════════════════════════════════════════════╣
║  👥 Tracked Influencers                                    ║
║  • Sant Manukyan (Macro)                                   ║
║  • Michael Saylor (Value)                                  ║
║  • Raoul Pal (Macro)                                       ║
╚═══════════════════════════════════════════════════════════╝
```

**Click ⚙️ Admin** to see the data behind these signals!

---

## ⚙️ Admin Dashboard Interface Map

```
╔═══════════════════════════════════════════════════════════╗
║ 🎯 Finclator │ 📊 Dashboard ⚙️ Admin 📖 Docs ❤️          ║
╠═══════════════════════════════════════════════════════════╣
║  🎛️ Finclator Admin Dashboard                            ║
║  Database Management & Real-time Monitoring                ║
╠═══════════════════════════════════════════════════════════╣
║ 📊 Overview │ 💬 Tweets │ 🎯 Predictions │ 💹 Prices │   ║
║ 🏆 Trust Scores │ ✅ Outcomes │ 📈 Monitoring            ║
╠═══════════════════════════════════════════════════════════╣
║                                                             ║
║  [Current Tab Content Displays Here]                       ║
║                                                             ║
║  • Overview: Stats + Charts                                ║
║  • Tweets: Searchable table with export                    ║
║  • Predictions: All sentiment data                         ║
║  • Prices: OHLCV data + charts                             ║
║  • Trust Scores: Performance metrics                       ║
║  • Outcomes: Evaluation results                            ║
║  • Monitoring: Real-time pipeline status                   ║
║                                                             ║
╚═══════════════════════════════════════════════════════════╝
```

**7 tabs** — Click any tab to switch views!

---

## 📖 API Docs Interface Map

```
╔═══════════════════════════════════════════════════════════╗
║ 🎯 Finclator │ 📊 Dashboard ⚙️ Admin 📖 Docs ❤️          ║
╠═══════════════════════════════════════════════════════════╣
║  FastAPI - Swagger UI                                      ║
╠═══════════════════════════════════════════════════════════╣
║                                                             ║
║  ▼ signals                                                 ║
║    GET /signals                Get overall signal          ║
║    GET /signals/school-signals Get school signals          ║
║                                                             ║
║  ▼ influencers                                             ║
║    GET /influencers            List all influencers        ║
║    GET /influencers/{id}       Get influencer details      ║
║                                                             ║
║  ▼ admin                                                   ║
║    GET /admin/stats            Database statistics         ║
║    GET /admin/tweets           Tweets data                 ║
║    GET /admin/predictions      Predictions data            ║
║    ...and more                                             ║
║                                                             ║
║  ▼ health                                                  ║
║    GET /health                 System health check         ║
║                                                             ║
╚═══════════════════════════════════════════════════════════╝
```

**Click any endpoint** to test it interactively!

---

## 🔄 Common Navigation Paths

### Path 1: Quick Signal Check
```
Start → Dashboard → View signals → Done
        └─(30s)─┘
     (auto-refresh)
```

### Path 2: Deep Dive Investigation
```
Dashboard → See signal
    │
    ├─ Click "⚙️ Admin"
    │
    ├─ Tab: 💬 Tweets (see source)
    │
    ├─ Tab: 🎯 Predictions (see sentiment)
    │
    ├─ Tab: 🏆 Trust Scores (see performance)
    │
    └─ Tab: ✅ Outcomes (see accuracy)
```

### Path 3: API Development
```
Docs → Test endpoint
  │
  ├─ Click "⚙️ Admin"
  │
  ├─ Tab: 📊 Overview (verify data)
  │
  └─ Click "📖 API Docs" (continue testing)
```

### Path 4: System Monitoring
```
Admin → Tab: 📈 Monitoring
   │
   ├─ Check 24h activity
   │
   ├─ Review pipeline status
   │
   └─ Click "📊 Dashboard" (verify signals)
```

### Path 5: Data Export
```
Admin → Tab: 💬 Tweets
   │
   ├─ Apply filters
   │
   ├─ Click "📥 Export CSV"
   │
   └─ Open in Excel/Numbers
```

---

## 🎯 Click Targets Reference

### Navigation Bar (Always Available)
```
┌────────────┬────────────┬────────────┬────────────┐
│ 📊        │ ⚙️         │ 📖         │ ❤️         │
│ Dashboard  │ Admin      │ API Docs   │ Health     │
├────────────┼────────────┼────────────┼────────────┤
│ Signals    │ 7 Tabs     │ Test API   │ Status     │
│ Schools    │ Tables     │ Schemas    │ Check      │
│ Live       │ Charts     │ Try Now    │ JSON       │
└────────────┴────────────┴────────────┴────────────┘
```

### Admin Dashboard Tabs
```
┌──────┬────────┬────────┬────────┬────────┬────────┬────────┐
│ 📊   │ 💬     │ 🎯     │ 💹     │ 🏆     │ ✅     │ 📈     │
│Overvi│Tweets  │Predict │Prices  │Trust   │Outcome │Monitor │
│ew    │        │ions    │        │Scores  │s       │ing     │
└──────┴────────┴────────┴────────┴────────┴────────┴────────┘
```

---

## 🚦 Color Coding

### Signal Labels
```
┌─────────┬─────────┬─────────┐
│  BUY    │ NEUTRAL │  SELL   │
│ 🟢 Green│ 🟡 Yellow│ 🔴 Red  │
└─────────┴─────────┴─────────┘
```

### Status Indicators
```
┌──────────────┬──────────────┐
│ ✓ Processed  │ ⏳ Pending   │
│ 🟢 Green     │ 🟡 Orange    │
└──────────────┴──────────────┘
```

### Outcome Labels
```
┌─────────┬─────────┬─────────┐
│ CORRECT │ UNCLEAR │  WRONG  │
│ 🟢 Green│ 🟡 Yellow│ 🔴 Red  │
└─────────┴─────────┴─────────┘
```

---

## 📱 Mobile Navigation

```
╔═══════════════════════════════════╗
║  🎯 Finclator    ☰               ║
╠═══════════════════════════════════╣
║  [Tap ☰ for menu]                ║
║                                   ║
║  • 📊 Dashboard                  ║
║  • ⚙️ Admin                      ║
║  • 📖 API Docs                   ║
║  • ❤️ Health                     ║
║                                   ║
╚═══════════════════════════════════╝
```

*Note: Mobile navigation maintains same structure*

---

## ⌨️ Keyboard Tips

### Browser Shortcuts
```
Cmd/Ctrl + L    → Focus address bar (type URL)
Cmd/Ctrl + R    → Refresh current page
Cmd/Ctrl + T    → New tab (open multiple interfaces)
Cmd/Ctrl + Tab  → Switch between tabs
```

### Recommended Tab Setup
```
Tab 1: 📊 Dashboard (auto-refresh)
Tab 2: ⚙️ Admin (monitoring)
Tab 3: 📖 API Docs (testing)
Tab 4: 💻 Terminal (logs)
```

---

## 🎨 Visual Hierarchy

```
┌─────────────────────────────────────────────┐
│ Level 1: Navigation Bar (Site-wide)        │ ← Always visible
├─────────────────────────────────────────────┤
│ Level 2: Page Header (Context)             │ ← Current page
├─────────────────────────────────────────────┤
│ Level 3: Tabs/Sections (Admin only)        │ ← Sub-navigation
├─────────────────────────────────────────────┤
│ Level 4: Content (Tables, Charts, etc.)    │ ← Main content
├─────────────────────────────────────────────┤
│ Level 5: Actions (Buttons, Filters, etc.)  │ ← Interactions
└─────────────────────────────────────────────┘
```

---

## 🔗 URL Structure

```
http://localhost:8000/
                      ├── dashboard      (User signals view)
                      ├── admin          (Admin management)
                      ├── docs           (API documentation)
                      ├── health         (Status check)
                      │
                      ├── signals        (API: get signals)
                      ├── influencers    (API: get influencers)
                      │
                      └── admin/
                            ├── stats
                            ├── tweets
                            ├── predictions
                            ├── price-candles
                            ├── trust-scores
                            ├── outcomes
                            └── pipeline-status
```

---

## ✅ Navigation Checklist

Before each session, verify:

- [ ] Server running: `curl http://localhost:8000/health`
- [ ] Navigation bar visible on all pages
- [ ] Links work (click each one)
- [ ] Active page highlighted in nav bar
- [ ] Dashboard auto-refresh working (30s)
- [ ] Admin tabs switch correctly
- [ ] Health check opens in new tab

---

## 🎯 Quick Start Guide

1. **Start server**:
   ```bash
   cd /Users/jakdemir/projects/finclator
   source .venv/bin/activate
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Open dashboard**: http://localhost:8000/dashboard

3. **Navigate**: Click any link in the nav bar

4. **Explore**: Use tabs in admin, try API in docs

5. **Monitor**: Check health anytime with ❤️ link

---

**🎉 That's it! You now have seamless navigation across all Finclator interfaces.**

**Start here**: http://localhost:8000/dashboard

**Last Updated**: 2025-11-15

