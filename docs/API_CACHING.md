# API Response Caching

Finclator implements local filesystem caching for all external API responses to avoid hitting rate limits and improve performance.

## Why Caching?

**External API Rate Limits:**
- **X API** (Free): 1,500 tweets/month, 50 requests/15min
- **Alpha Vantage** (Free): 25 requests/day, 5 requests/minute
- **Hugging Face** (Free): 30,000 requests/month

**Benefits:**
- ✅ Avoid rate limit errors
- ✅ Faster response times (no network calls)
- ✅ Work offline during development
- ✅ Reduce costs (if using paid tiers)
- ✅ Consistent results for same inputs

## How It Works

### Cache Location
```
.cache/
├── alphavantage/     # Price data (24h TTL)
├── huggingface/      # Sentiment results (30d TTL)
└── x_api/           # Tweet data (6h TTL)
```

### Cache Keys
Responses are cached using MD5 hash of:
- API name (`alphavantage`, `huggingface`, `x_api`)
- Request parameters (sorted JSON)

Example: `alphavantage:{"asset":"BTC","outputsize":"compact"}` → `a1b2c3d4...json`

### Time-to-Live (TTL)

| API | TTL | Reasoning |
|-----|-----|-----------|
| **Alpha Vantage** | 90 days (3 months) | Historical price data rarely changes |
| **Hugging Face** | 90 days (3 months) | Sentiment for same text never changes |
| **X API** | 90 days (3 months) | Historical tweets are immutable |

### Cache Flow

```
┌─────────────┐
│ Worker/API  │
└──────┬──────┘
       │
       ├──> Check Cache
       │     │
       │     ├─ HIT ──> Return cached data ✅
       │     │
       │     └─ MISS ─> Call External API
       │                  │
       │                  ├─ Store in cache
       │                  └─ Return data
       │
       v
   Continue processing
```

## Usage

### Automatic Caching

Caching is automatic for all external API calls:

```python
# Example: Sentiment classification automatically uses cache
from src.services.sentiment_classifier import SentimentClassifier

classifier = SentimentClassifier()
result = await classifier.classify_sentiment(
    "Bitcoin going to $100k!",
    "BTC"
)
# First call: Makes API request, caches result
# Second call (same text): Returns cached result instantly
```

### Manual Cache Control

```python
from src.services.api_cache import api_cache

# Check cache statistics
stats = api_cache.get_stats()
print(f"Total cached: {sum(s['total_entries'] for s in stats.values())}")

# Invalidate specific cache entry
await api_cache.invalidate(
    'huggingface',
    {'text': 'Bitcoin to $100k', 'model': 'ProsusAI/finbert'}
)

# Clear all cache for an API
await api_cache.invalidate('alphavantage')
```

### View Cache Stats

```bash
python scripts/cache_stats.py
```

Output:
```
📊 API Cache Statistics
============================================================

ALPHAVANTAGE:
  Entries: 3
  Location: .cache/alphavantage

HUGGINGFACE:
  Entries: 23
  Location: .cache/huggingface

============================================================
Total cached responses: 26
```

## Cache Behavior Examples

### Alpha Vantage (Price Data)

**First run:**
```
2025-11-15 - INFO - Fetching price data for BTC
2025-11-15 - INFO - [API Call] Alpha Vantage: BTC
2025-11-15 - DEBUG - Cache STORED: alphavantage
2025-11-15 - INFO - Ingested 350 candles for BTC
```

**Second run (within 24h):**
```
2025-11-15 - INFO - Fetching price data for BTC
2025-11-15 - INFO - Cache HIT: alphavantage - cached 120s ago
2025-11-15 - INFO - Ingested 350 candles for BTC
```

**After 24h:**
```
2025-11-16 - INFO - Fetching price data for BTC
2025-11-16 - DEBUG - Cache EXPIRED: alphavantage
2025-11-16 - INFO - [API Call] Alpha Vantage: BTC
2025-11-16 - INFO - Ingested 350 candles for BTC
```

### Hugging Face (Sentiment)

**First classification:**
```
- INFO - Classifying sentiment for BTC: Bitcoin breaking out...
- INFO - [API Call] Hugging Face FinBERT
- INFO - Classified as BUY (SHORT) with confidence 0.86
- DEBUG - Cache STORED: huggingface
```

**Same tweet again (anytime within 30 days):**
```
- INFO - Classifying sentiment for BTC: Bitcoin breaking out...
- INFO - Cache HIT: huggingface - cached 3600s ago
- INFO - Classified as BUY (SHORT) with confidence 0.86
```

## Development Tips

### Clear Cache During Development

```bash
# Remove all cached data
rm -rf .cache/

# Or selectively:
rm -rf .cache/huggingface/  # Re-classify all tweets
rm -rf .cache/alphavantage/  # Re-fetch prices
```

### Force Fresh Data

Set TTL to 0 temporarily in `api_cache.py`:

```python
self.ttl_config = {
    "x_api": timedelta(seconds=0),  # Always fetch fresh
    "alphavantage": timedelta(seconds=0),
    "huggingface": timedelta(seconds=0),
}
```

### Cache During Testing

Mock data automatically uses cache:

```bash
# Create mock tweets
python scripts/create_mock_tweets.py

# First sentiment run: Creates cache
python -m src.workers.sentiment

# Second run: Uses cache (instant)
python -m src.workers.sentiment
```

## Production Considerations

### Cache Size

Monitor cache directory size:

```bash
du -sh .cache/
# 15M  .cache/
```

Typical sizes:
- Alpha Vantage: ~500KB per asset per day
- Hugging Face: ~1KB per tweet
- X API: ~2KB per tweet batch

### Cache Location

For production, consider:

```python
# Use absolute path
APICache(cache_dir="/var/cache/finclator/api")

# Or environment variable
APICache(cache_dir=os.getenv("CACHE_DIR", ".cache/api"))
```

### Monitoring

Add cache hit rate monitoring:

```python
total_requests = cache_hits + cache_misses
hit_rate = cache_hits / total_requests * 100
logger.info(f"Cache hit rate: {hit_rate:.1f}%")
```

Ideal hit rates:
- **Alpha Vantage**: 95%+ (same daily data requested often)
- **Hugging Face**: 80%+ (some tweet duplication)
- **X API**: 50%+ (depends on refresh frequency)

## Troubleshooting

### Cache Not Working

**Check permissions:**
```bash
ls -la .cache/
# Should be writable
```

**Check disk space:**
```bash
df -h .
```

### Stale Data

**Clear expired cache:**
```python
# Manually expire all cache
from src.services.api_cache import api_cache
import asyncio

asyncio.run(api_cache.invalidate('alphavantage'))
```

### Rate Limits Still Hit

**Verify cache is enabled:**
```bash
# Should see "Cache HIT" in logs
python -m src.workers.price_ingestion | grep -i cache
```

**Check TTL configuration:**
```python
# In api_cache.py
print(api_cache.ttl_config)
```

## Advanced Usage

### Custom Cache for Worker

```python
from src.services.api_cache import APICache

# Create separate cache instance
worker_cache = APICache(cache_dir=".cache/worker")

# Use with custom TTL
worker_cache.ttl_config['custom_api'] = timedelta(hours=12)
```

### Preload Cache

```python
# Fetch and cache all prices before main pipeline
assets = ['BTC', 'GOLD', 'SPX']
for asset in assets:
    await price_provider.fetch_daily_candles(asset)
```

### Cache Warming Script

```bash
# cache_warmup.sh
python -m src.workers.price_ingestion
python scripts/create_mock_tweets.py
python -m src.workers.sentiment
echo "Cache warmed up for development"
```

## Summary

✅ **Automatic** - No code changes needed, works transparently  
✅ **Smart TTLs** - Different expiry for different APIs  
✅ **Disk-based** - Survives restarts, shareable across processes  
✅ **Monitored** - Easy to view stats and debug  
✅ **Safe** - Atomic writes, handles errors gracefully  

**Result**: Finclator can run indefinitely without hitting rate limits! 🚀

