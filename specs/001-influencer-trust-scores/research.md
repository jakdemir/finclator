# Research & Design Decisions: Finclator Influencer Trust-Scoring MVP

## Tech Stack & Hosting

**Decision**: Use Python 3.11 with FastAPI for the HTTP API and a separate Python worker process, both deployed on Render, backed by a single Render PostgreSQL instance.  
**Rationale**: FastAPI is a lightweight, well-supported framework for JSON APIs with good async support; Python aligns well with data processing and ML-adjacent workloads. Render simplifies deployment and cron scheduling without introducing extra infrastructure layers. A single database instance keeps the MVP architecture simple and focused on core prediction logic.  
**Alternatives considered**:  
- Node.js/TypeScript + Express/Nest: strong for APIs but less natural for numeric/analysis-heavy code in this domain.  
- Serverless (e.g., AWS Lambda + RDS): more operational complexity for this stage and less straightforward for long-running batch jobs.  
- Multiple databases (e.g., separate analytics DB): rejected as premature complexity for MVP.

## External Services & Integrations

**Decision**: Use the X API (or x.ai cookbook stream approach) for influencer tweet ingestion, grok-3-fast and grok-3-mini for sentiment analysis, and Alpha Vantage for OHLCV price data for BTC, GOLD, and SPX.  
**Rationale**: These services directly provide the data and language capabilities required by the spec with minimal custom model work. Using a fast/mini model pair allows noise-filtering and structured classification while keeping latency and cost manageable. Alpha Vantage offers straightforward access to historical and intraday prices suitable for the initial calibration logic.  
**Alternatives considered**:  
- Building a custom sentiment model: rejected for MVP as it violates Simplicity & Focus and would delay validation of the trust-scoring concept.  
- Other price APIs (Yahoo Finance, Polygon, etc.): possible substitutes but not required to decide now; the abstraction is kept in a `price_provider` service.

## Trust Scoring & Evaluation

**Decision**: Evaluate each prediction by comparing asset price at tweet time to price over a fixed window defined by the tweet’s time horizon (short, medium, long), then classify outcomes as CORRECT, WRONG, or UNCLEAR; maintain a rolling performance-based trust score per influencer (and possibly per asset/horizon) based on these outcomes.  
**Rationale**: This approach directly links sentiments to realized price movements, matching the Data-Driven Trust principle. Using discrete outcomes and rolling scores keeps the implementation tractable while still capturing predictive skill over time.  
**Alternatives considered**:  
- Continuous scoring based on exact return magnitude: more expressive but adds model complexity and interpretation overhead for MVP.  
- Pure ranking without explicit outcomes: less transparent and harder to audit against concrete correctness criteria.

## Aggregation & Exposure

**Decision**: Aggregate trust-weighted predictions first at the finance school level and then into overall asset + horizon indicators; expose only a minimal set of JSON endpoints (`/signals`, `/school-signals`, `/influencers/{id}`) without authentication or UI.  
**Rationale**: School-level aggregation reflects the conceptual “worldview” layer from the spec and preserves interpretability. Restricting the surface to a few read-only endpoints keeps the MVP focused and easy to reason about.  
**Alternatives considered**:  
- Building dashboards or interactive web UIs: deferred to keep the MVP aligned with Simplicity & Focus.  
- Exposing raw tweet-level data via API: possible later but not necessary for validating the trust-scoring abstraction.


