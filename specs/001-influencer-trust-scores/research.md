# Research: Finclator Influencer Trust-Scoring MVP

**Date**: 2025-11-30  
**Feature**: 001-influencer-trust-scores

This document consolidates technical research and decisions made during the planning phase.

## Technology Stack Decisions

### Python 3.11 + FastAPI

**Decision**: Use Python 3.11 with FastAPI for the API service.

**Rationale**:
- Python ecosystem provides excellent libraries for data processing, ML/AI integration (Hugging Face), and async HTTP clients
- FastAPI offers automatic OpenAPI documentation, async support, and high performance
- Async/await pattern aligns with I/O-bound operations (database, external APIs)
- Type hints and Pydantic provide runtime validation and better developer experience

**Alternatives Considered**:
- **Node.js/Express**: Rejected - Python ecosystem better for ML/AI integrations (Hugging Face, sentiment analysis)
- **Go**: Rejected - More complex for rapid MVP development; Python libraries more mature for this domain
- **Django**: Rejected - Too heavy for a read-only API; FastAPI is lighter and more performant

### SQLAlchemy 2.0 + asyncpg

**Decision**: Use SQLAlchemy 2.0 with asyncpg for PostgreSQL database access.

**Rationale**:
- SQLAlchemy 2.0 provides modern async/await API with type hints
- asyncpg is the fastest async PostgreSQL driver for Python
- ORM provides data model abstraction while maintaining query flexibility
- Alembic integration for database migrations

**Alternatives Considered**:
- **Django ORM**: Rejected - Tied to Django framework; SQLAlchemy more flexible
- **Tortoise ORM**: Rejected - Less mature ecosystem; SQLAlchemy has better documentation
- **Raw asyncpg**: Rejected - Too low-level; ORM provides better maintainability

### PostgreSQL

**Decision**: Use PostgreSQL as the primary database.

**Rationale**:
- ACID compliance for financial data integrity
- Excellent support for JSON/arrays (for asset_symbols arrays)
- Strong performance for time-series data (price candles, timestamps)
- Widely supported on cloud platforms (Render, AWS, etc.)

**Alternatives Considered**:
- **SQLite**: Rejected - Not suitable for production scale; limited concurrency
- **MongoDB**: Rejected - Relational data model better fits entity relationships; PostgreSQL sufficient
- **TimescaleDB**: Rejected - Overkill for MVP; can migrate later if needed

### External API Integrations

#### X API (Twitter) v2

**Decision**: Use X API v2 for fetching influencer tweets.

**Rationale**:
- Official API provides reliable access to tweet data
- Rate limits manageable with caching strategy (50 req/15min free tier)
- Supports filtering by user, date ranges, and tweet fields

**Alternatives Considered**:
- **Web scraping**: Rejected - Violates ToS; unreliable; rate limits harder to manage
- **Third-party aggregators**: Rejected - Additional cost; less control over data freshness

**Caching Strategy**: Local filesystem cache (`.cache/api/x_api/`) to minimize API calls and handle rate limits gracefully.

#### Alpha Vantage

**Decision**: Use Alpha Vantage for OHLCV price data.

**Rationale**:
- Free tier available (5 req/min)
- Provides historical and real-time data for BTC, Gold (via GLD), and S&P 500 (via SPY)
- Simple REST API with JSON responses

**Alternatives Considered**:
- **Yahoo Finance API**: Rejected - Unofficial; unreliable; frequent breaking changes
- **Polygon.io**: Rejected - Paid service; overkill for MVP
- **CoinGecko (for BTC)**: Rejected - Would need multiple providers; Alpha Vantage covers all assets

**Caching Strategy**: Local filesystem cache (`.cache/api/alphavantage/`) to minimize API calls and provide fallback when rate-limited.

#### Hugging Face (FinBERT)

**Decision**: Use Hugging Face FinBERT model for sentiment classification.

**Rationale**:
- FinBERT is pre-trained on financial text, making it suitable for market sentiment
- Hugging Face provides easy integration via `transformers` library
- Can run locally or via API (free tier available)
- Better than generic sentiment models for financial domain

**Alternatives Considered**:
- **OpenAI GPT models**: Rejected - More expensive; overkill for simple classification
- **VADER (rule-based)**: Rejected - Less accurate for financial domain-specific language
- **Custom model training**: Rejected - Too complex for MVP; FinBERT already domain-adapted

### Architecture Patterns

#### Worker Scripts vs. Task Queue

**Decision**: Use simple Python scripts for background jobs instead of a task queue (Celery, RQ).

**Rationale**:
- Simpler deployment and debugging
- No additional infrastructure (Redis, RabbitMQ)
- Can be scheduled via cron or Render Cron Jobs
- Aligns with "Simplicity & Focus" principle

**Alternatives Considered**:
- **Celery + Redis**: Rejected - Additional infrastructure complexity; not needed for MVP
- **RQ (Redis Queue)**: Rejected - Same as above
- **AWS Lambda/Scheduled Functions**: Rejected - Vendor lock-in; simple scripts more portable

**Future Consideration**: If scale requires, can migrate to task queue later without changing core logic.

#### Local Filesystem Caching

**Decision**: Use local filesystem for API response caching instead of Redis/Memcached.

**Rationale**:
- No additional infrastructure
- Persists across restarts
- Simple to implement and debug
- Sufficient for MVP scale (50+ influencers, 10k tweets/month)

**Alternatives Considered**:
- **Redis**: Rejected - Additional infrastructure; not needed for MVP
- **In-memory cache**: Rejected - Lost on restart; filesystem more durable
- **Database cache table**: Rejected - Adds complexity; filesystem simpler

**Future Consideration**: Can migrate to Redis if caching becomes a bottleneck.

### Trust Score Calculation

**Decision**: Calculate trust scores using all historical data (no time window limit).

**Rationale**:
- More data = more accurate trust scores
- Historical performance is the core value proposition
- No need to decay old predictions (all predictions matter equally)

**Alternatives Considered**:
- **Rolling window (e.g., last 6 months)**: Rejected - Loses valuable historical data; spec clarification confirmed "all historical data"
- **Exponential decay**: Rejected - Adds complexity; no clear benefit for MVP
- **Time-weighted (recent predictions matter more)**: Rejected - Not aligned with spec requirement

### Sentiment Classification Approach

**Decision**: Use LLM-based classification (FinBERT) to extract direction (BUY/NEUTRAL/SELL) and time horizon (SHORT/MEDIUM/LONG) from tweets.

**Rationale**:
- Financial tweets often use implicit language ("bullish", "bearish", "long-term", "short-term")
- Rule-based extraction would miss nuanced signals
- FinBERT understands financial domain language

**Alternatives Considered**:
- **Keyword matching**: Rejected - Too simplistic; misses context and nuance
- **Regex patterns**: Rejected - Same as above
- **Manual labeling**: Rejected - Not scalable for 10k+ tweets/month

## Performance Considerations

### API Response Time

**Target**: <500ms p95 for indicator endpoints.

**Approach**:
- Pre-computed `CurrentSignal` table (updated by aggregation worker)
- Database indexes on (asset_symbol, horizon) for fast lookups
- Minimal joins (signals pre-aggregated)

### Data Ingestion Scale

**Target**: 50+ influencers, 10,000+ tweets/month.

**Approach**:
- Batch processing in workers
- Rate limit handling with exponential backoff
- Caching to minimize API calls
- Async I/O for parallel processing where possible

### Trust Score Recalculation

**Target**: Weekly batch job.

**Approach**:
- Incremental calculation (only evaluate new predictions)
- Database indexes on (influencer_id, asset_symbol, horizon) for fast queries
- Can run during off-peak hours

## Security & Privacy

### API Keys

**Decision**: Store API keys in environment variables (`.env` file), never commit to git.

**Rationale**:
- Standard practice for sensitive credentials
- `.env` in `.gitignore`
- Easy to configure per environment (local, staging, production)

### Data Privacy

**Decision**: Store only public tweet data (text, timestamp, author); no private user data.

**Rationale**:
- Tweets are public by nature
- No PII collection required
- Complies with X API ToS for public data access

## Deployment Strategy

### Render.com

**Decision**: Deploy to Render.com (PostgreSQL + Web Service + Cron Jobs).

**Rationale**:
- Simple deployment (git push)
- Managed PostgreSQL
- Built-in cron job support
- Free tier available for MVP

**Alternatives Considered**:
- **AWS (ECS/Lambda)**: Rejected - More complex setup; overkill for MVP
- **Heroku**: Rejected - No longer free tier; Render more cost-effective
- **Self-hosted**: Rejected - Operational overhead; managed services better for MVP

## Summary

All technical decisions prioritize simplicity and focus on core value delivery. The stack is proven, well-documented, and can scale to the specified requirements (50+ influencers, 10k+ tweets/month) without premature optimization. Future enhancements (task queues, Redis caching) can be added incrementally if needed.

