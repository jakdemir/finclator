# X (Twitter) API Setup Guide

This guide explains how to get an X API key for Finclator to fetch real tweets from influencers.

---

## Why X API?

Finclator needs access to the X (Twitter) API to:
- Fetch recent tweets from configured influencers
- Monitor market sentiment in real-time
- Build trust scores based on actual predictions

---

## Getting an X API Key

### Step 1: Apply for X Developer Account

1. Go to the [X Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Sign in with your X (Twitter) account
3. Click **"Sign up for Free Account"** if you don't have developer access
4. Fill out the application form:
   - **What's your use case?** Academic Research / Financial Analysis
   - **Describe your use case**: "Building a trust-scoring system for financial market predictions from public tweets"
   - **Will you display tweets?** No (just analyzing sentiment)
   - **Will you use the Twitter API for analysis?** Yes

### Step 2: Create a Project & App

1. Once approved, go to the [Developer Portal Dashboard](https://developer.twitter.com/en/portal/projects-and-apps)
2. Click **"+ Create Project"**
3. Give your project a name: "Finclator"
4. Under "Use Case", select: **"Exploring the API"**
5. Create an App within the project: "Finclator API"

### Step 3: Get Your Bearer Token

1. In your app's "Keys and tokens" section
2. Copy the **Bearer Token** (this is your `X_API_BEARER_TOKEN`)
3. Save it securely - you won't be able to see it again

### Step 4: Add to Finclator

Add the bearer token to your `.env` file:

```bash
X_API_BEARER_TOKEN=your_bearer_token_here
```

Or set it as an environment variable:

```bash
export X_API_BEARER_TOKEN="your_bearer_token_here"
```

---

## API Access Levels

X offers different API access tiers:

### Free Tier (Recommended for MVP)
- ✅ **Tweet lookup**: Read tweets from public accounts
- ✅ **User lookup**: Get user IDs from usernames
- ❌ Limits: 100 requests per app per month (very limited!)

### Basic Tier ($100/month)
- ✅ **10,000 tweets per month**
- ✅ **3,000 requests per month**
- ✅ Enough for ~10-20 influencers

### Pro Tier ($5,000/month)
- ✅ **1,000,000 tweets per month**
- ✅ **300,000 requests per month**
- ✅ Suitable for production use

**For Development**: Use Free or Basic tier  
**For Production**: Consider Basic or Pro based on influencer count

---

## Rate Limits

Finclator handles rate limiting automatically through:
- **API Caching**: Responses cached locally for 3 months
- **Smart Fetching**: Only fetches new tweets since last run
- **Exponential Backoff**: Retries with delays on rate limit errors

### Avoiding Rate Limits

1. **Cache tweets locally** (already implemented) ✅
2. **Run ingestion infrequently** (e.g., once per hour, not every minute)
3. **Limit influencer count** in Free tier (max 5-10 influencers)
4. **Use mock data for testing** (already implemented) ✅

---

## Testing X API Integration

### 1. Verify API Key

```bash
curl -H "Authorization: Bearer YOUR_BEARER_TOKEN" \
  "https://api.twitter.com/2/users/by/username/SantManukyan"
```

Expected response:
```json
{
  "data": {
    "id": "123456789",
    "name": "Sant Manukyan",
    "username": "SantManukyan"
  }
}
```

### 2. Test Tweet Fetching

```bash
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate
python -m src.workers.tweet_ingestion
```

Expected output:
```
Fetching tweets for SantManukyan
Fetched 10 tweets for @SantManukyan (since 2025-11-08)
Ingested tweet 1234... from SantManukyan (assets: BTC, GOLD)
Tweet ingestion complete - 10 new tweets ingested
```

### 3. Check Cache

```bash
python scripts/cache_stats.py
```

You should see cached X API responses.

---

## Troubleshooting

### Error: 401 Unauthorized

**Cause**: Invalid or expired bearer token  
**Fix**: Regenerate bearer token in X Developer Portal

### Error: 429 Too Many Requests

**Cause**: Rate limit exceeded  
**Fix**: 
- Wait 15 minutes for rate limit reset
- Check cache is working: `ls -la .cache/api/x_api/`
- Reduce ingestion frequency

### Error: 403 Forbidden

**Cause**: App doesn't have required permissions  
**Fix**: 
- Ensure you have "Read" permissions enabled in app settings
- Check your API tier supports the endpoint

### No Tweets Found

**Cause**: User hasn't tweeted recently or username is incorrect  
**Fix**:
- Verify username is correct (without @)
- Check user's X profile is public
- Increase `since_hours` parameter

---

## Alternative: Using Mock Data

If you don't have X API access yet, use mock tweets for testing:

```bash
python scripts/create_mock_tweets.py
```

This creates realistic sample tweets for all influencers without requiring X API access.

---

## Production Deployment

When deploying to Render:

1. Add `X_API_KEY` to your Render environment variables
2. Set appropriate cron schedule for tweet ingestion (e.g., `0 * * * *` for hourly)
3. Monitor API usage in X Developer Portal
4. Set up alerts for rate limit warnings

---

## Security Best Practices

- ✅ **Never commit** API keys to Git
- ✅ **Use environment variables** or secrets management
- ✅ **Rotate keys regularly** (every 3-6 months)
- ✅ **Monitor usage** to detect unauthorized access
- ❌ **Don't share** bearer tokens publicly

---

## Resources

- [X API Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [Rate Limits Reference](https://developer.twitter.com/en/docs/twitter-api/rate-limits)
- [X Developer Portal](https://developer.twitter.com/en/portal/dashboard)
- [Finclator API Caching Docs](./API_CACHING.md)

---

**Questions?** Check the X Developer Forum or Finclator GitHub Issues.

