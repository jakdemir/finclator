# Hugging Face Setup Guide

Finclator uses **Hugging Face Inference API** with the **FinBERT** model for financial sentiment analysis.

## Why Hugging Face + FinBERT?

- ✅ **100% Free**: 30,000 requests/month
- ✅ **Financial-Specific**: FinBERT is trained on financial text
- ✅ **Fast**: ~1-2 seconds per classification
- ✅ **No Credit Card**: Sign up with just email
- ✅ **Accurate**: Better than general-purpose LLMs for financial sentiment

## Step 1: Get Your Free API Key

### 1.1 Create Hugging Face Account

Visit: https://huggingface.co/join

- Sign up with email (free, no credit card)
- Verify your email

### 1.2 Generate API Token

1. Go to: https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Name: `finclator-api`
4. Type: **Read** (default)
5. Click **"Generate"**
6. Copy your token (starts with `hf_...`)

**Example token:**
```
hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

⚠️ **Important**: Keep this token secret! Don't commit it to git.

---

## Step 2: Add to Finclator

### 2.1 Update `.env` File

```bash
cd /Users/jakdemir/projects/finclator
nano .env  # or use your preferred editor
```

Update this line:
```bash
HUGGINGFACE_API_KEY=hf_your_actual_token_here
```

**Full `.env` example:**
```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://localhost/finclator

# External API Keys
X_API_KEY=your_x_api_key_here
ALPHAVANTAGE_API_KEY=your_alphavantage_api_key_here
HUGGINGFACE_API_KEY=hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890  # Your real token

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

---

## Step 3: Test It

```bash
cd /Users/jakdemir/projects/finclator
source .venv/bin/activate

# Test sentiment classification
python scripts/test_sentiment.py
```

**Expected output:**
```
🧪 Testing Hugging Face Sentiment Classification

============================================================

📝 Test 1/5
Tweet: "Bitcoin is breaking out! ATH incoming, load up now!"
Asset: BTC
Market Relevant: ✓ Yes
Direction: BUY
Horizon: SHORT
Confidence: 87.32%
------------------------------------------------------------

📝 Test 2/5
Tweet: "Gold hitting new all-time highs. Bullish for the next 5 years."
Asset: GOLD
Market Relevant: ✓ Yes
Direction: BUY
Horizon: LONG
Confidence: 92.14%
------------------------------------------------------------

...
```

---

## How It Works

### Sentiment Classification

Finclator uses **ProsusAI/finbert**, a BERT model fine-tuned on financial texts:

```python
from huggingface_hub import InferenceClient

client = InferenceClient(token="hf_your_token")

# Classify financial sentiment
result = client.text_classification(
    "Bitcoin going to $100k!",
    model="ProsusAI/finbert"
)

# Result: [{'label': 'positive', 'score': 0.89}]
# Mapped to: BUY with 89% confidence
```

### Label Mapping

| FinBERT Output | Finclator Direction |
|----------------|---------------------|
| `positive` | `BUY` |
| `negative` | `SELL` |
| `neutral` | `NEUTRAL` |

### Horizon Detection

Time horizon is detected from keywords:

**SHORT (0-3 months):**
- "today", "this week", "soon", "immediate"
- "in 2 days", "next week"

**MEDIUM (3-12 months):**
- Default if no explicit horizon
- "in 6 months", "this year"

**LONG (1-5+ years):**
- "long term", "years", "decade", "cycle"
- "next bull cycle", "hodl"

---

## Rate Limits

**Free Tier:**
- 30,000 requests/month
- ~1,000 requests/day
- ~40 requests/hour

**For Finclator:**
- 1 influencer × 50 tweets/day = **50 requests/day** ✅
- 10 influencers × 50 tweets/day = **500 requests/day** ✅
- Plenty of headroom!

**If you exceed limits:**
- Wait until next month (resets)
- Or use multiple tokens (create new HF accounts)
- Or implement local Ollama as fallback

---

## Troubleshooting

### Error: "Invalid token"

```python
huggingface_hub.utils._errors.HTTPError: 401 Client Error
```

**Solution:**
1. Check token in `.env` starts with `hf_`
2. Verify token is **Read** type
3. Regenerate token if needed

### Error: "Rate limit exceeded"

```python
huggingface_hub.utils._errors.HTTPError: 429 Too Many Requests
```

**Solution:**
- Wait ~1 hour
- Check usage: https://huggingface.co/settings/tokens
- Reduce tweet ingestion frequency

### Error: "Model loading"

```
Model ProsusAI/finbert is currently loading
```

**Solution:**
- First request wakes up the model (~20 seconds)
- Retry after 30 seconds
- Subsequent requests will be fast

---

## Alternative Models

You can swap FinBERT for other models:

### Twitter-Specific Sentiment
```python
self.sentiment_model = "cardiffnlp/twitter-roberta-base-sentiment-latest"
```

### Financial News Sentiment
```python
self.sentiment_model = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis"
```

Edit in `src/services/sentiment_classifier.py`:
```python
class SentimentClassifier:
    def __init__(self):
        self.client = InferenceClient(token=settings.huggingface_api_key)
        self.sentiment_model = "ProsusAI/finbert"  # Change this
```

---

## Production Tips

1. **Cache Results**: Store classifications to avoid re-processing
2. **Batch Requests**: Process multiple tweets in parallel
3. **Monitor Usage**: Check your token usage regularly
4. **Fallback Strategy**: Have Ollama ready for offline mode
5. **Error Handling**: Already implemented (returns None on failure)

---

## Cost Comparison

| Provider | Free Tier | Cost for 10k tweets |
|----------|-----------|---------------------|
| **Hugging Face** | **30k/month** | **$0** ✅ |
| Groq | 14.4k/day | $0 |
| OpenAI GPT-4o-mini | $5 credit | ~$1.50 |
| Grok (X.AI) | None | $25/month |

---

## Next Steps

Once your Hugging Face token is set up:

1. **Get X API Key**: To fetch real tweets
   - https://developer.twitter.com/en/portal/dashboard

2. **Get Alpha Vantage Key**: For price data
   - https://www.alphavantage.co/support/#api-key

3. **Run the Full Pipeline**:
   ```bash
   ./scripts/run_pipeline.sh
   ```

4. **Query Your Signals**:
   ```bash
   curl "http://localhost:8000/signals?asset=BTC&horizon=SHORT"
   ```

---

## Support

- **Hugging Face Docs**: https://huggingface.co/docs/api-inference
- **FinBERT Model**: https://huggingface.co/ProsusAI/finbert
- **Free Token Limits**: https://huggingface.co/pricing

**Happy sentiment analyzing!** 🚀

