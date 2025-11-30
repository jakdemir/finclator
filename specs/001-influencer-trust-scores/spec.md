# Feature Specification: Finclator Influencer Trust-Scoring MVP

**Feature Branch**: `001-influencer-trust-scores`  
**Created**: 2025-11-15  
**Status**: Draft  
**Input**: User description: "Finclator is a fintech application that generates Buy / Neutral / Sell market indicators for BTC, Gold, and the S&P 500 across short-term (0–3 months), medium-term (3–12 months), and long-term (1–5+ years) horizons. The purpose of the app is to translate influencer-driven market commentary into measurable, evidence-based predictions instead of subjective opinion. The system strictly analyzes each influencer’s tweets by extracting explicit sentiment signals tied to direction (buy, neutral, sell) and time horizon. Every extracted sentiment is systematically compared with actual market price movements following the timestamp of the tweet to evaluate whether the sentiment aligned with reality. Finclator uses this comparison to assign a performance-based trust score, rewarding influencers who consistently predict movements correctly and penalizing those who do not. Influencers are then grouped into different finance theory schools, allowing insights to be interpreted within their conceptual worldview rather than as isolated opinions. Finally, the app aggregates these calibrated trust scores within each school to form compounded prediction scores, which are used to generate final Buy / Neutral / Sell indicators for each asset and timeframe."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View calibrated market indicators (Priority: P1)

As a retail or professional investor, I want to view Buy / Neutral / Sell indicators for BTC, Gold, and the S&P 500 across different time horizons so that I can quickly understand the consensus signal derived from calibrated influencer predictions rather than raw opinions.

**Why this priority**: This is the core user-facing value of Finclator and must be available in the MVP for the product to be useful at all.

**Independent Test**: Can be fully tested by selecting each asset and time horizon and verifying that a Buy / Neutral / Sell indicator is displayed based on underlying calibrated trust scores and sentiment inputs.

**Acceptance Scenarios**:

1. **Given** that the system has processed historical influencer tweets and associated price data, **When** a user selects BTC and the short-term horizon, **Then** the system displays a single Buy / Neutral / Sell indicator derived from aggregated, trust-weighted sentiment within relevant finance schools.
2. **Given** that indicators exist for all three assets and time horizons, **When** a user switches between assets and horizons, **Then** the system updates the displayed indicator without requiring any additional configuration.

---

### User Story 2 - Inspect trust score and school breakdown (Priority: P2)

As an investor, I want to inspect how the indicator was formed (influencer trust scores, sentiment breakdown, and finance school contribution) so that I can judge whether to rely on the signal and understand the underlying conceptual worldviews.

**Why this priority**: Transparency and data-driven trust are essential to adoption; users must be able to see why a signal exists, not just the final label.

**Independent Test**: Can be fully tested by opening an indicator detail view for a given asset and horizon and verifying that influencer trust scores, sentiment counts, and school-level contributions are displayed and consistent with the underlying calibration rules.

**Acceptance Scenarios**:

1. **Given** that a Buy / Neutral / Sell indicator is displayed for BTC short-term, **When** a user opens the indicator details, **Then** the system shows (a) the list or summary of influencers contributing to the signal, (b) each influencer’s trust score, and (c) the net buy/neutral/sell contributions by finance school.
2. **Given** that some influencers have poor historical performance, **When** their contributions are shown in the detail view, **Then** their trust scores and weightings are visibly lower than those of consistently accurate influencers.

---

### User Story 3 - Continuously calibrate influencer trust scores (Priority: P3)

As a product owner or quantitative analyst, I want the system to automatically recalibrate each influencer’s trust score based on observed alignment between their stated sentiment and subsequent market movements so that indicators remain up to date and evidence-based over time.

**Why this priority**: Without ongoing calibration, trust scores become stale and indicators no longer reflect real predictive performance, undermining the product’s value.

**Independent Test**: Can be fully tested by feeding the system a controlled set of historical tweets and price movements, running the calibration process, and verifying that influencer trust scores and resulting indicators adjust according to their prediction accuracy.

**Acceptance Scenarios**:

1. **Given** a set of historical tweets where an influencer repeatedly predicts the correct direction and approximate time horizon of BTC moves, **When** the calibration process runs, **Then** that influencer’s trust score increases and their weight in future BTC indicators becomes higher.
2. **Given** a set of historical tweets where an influencer consistently predicts the wrong direction of S&P 500 moves, **When** the calibration process runs, **Then** that influencer’s trust score decreases and their contribution to S&P 500 indicators becomes negligible or zero.

---

### Edge Cases

- What happens when there is insufficient tweet or price data for a given asset, horizon, or influencer (e.g., new influencer or newly added asset)?
- How does the system handle conflicting sentiment signals (e.g., highly trusted influencers disagree on direction within the same horizon)?
- How does the system behave when market data is temporarily unavailable or delayed for one of the assets?
- What happens when a tweet’s time horizon cannot be reliably extracted or is ambiguous?
- How does the system handle influencers who change their handle or become inactive for long periods?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-101**: Use offline data data/TwExportly_santmanukyan_tweets_2025_11_30.csv for SantManukyan. Write it to database. make a sentiment analysis. check with market data. Assign a trust score.
- **FR-001**: System MUST ingest influencer tweets and extract explicit sentiment signals that include direction (buy, neutral, sell) and intended time horizon (short-, medium-, or long-term).
- **FR-002**: System MUST associate each extracted sentiment with the relevant asset (BTC, Gold, S&P 500) and timestamp it for subsequent performance evaluation.
- **FR-003**: System MUST compare each extracted sentiment with actual market price movements over the corresponding time horizon to determine whether the sentiment aligned with observed reality.
- **FR-004**: System MUST compute and maintain a performance-based trust score for each influencer that increases when predictions align with market movements and decreases when they do not.
- **FR-005**: System MUST assign each influencer to one or more finance theory schools so that their signals can be interpreted within a conceptual worldview.
- **FR-006**: System MUST aggregate trust-weighted sentiment within each finance school for each asset and time horizon to produce school-level prediction scores.
- **FR-007**: System MUST aggregate school-level prediction scores into a final Buy / Neutral / Sell indicator for each asset and time horizon.
- **FR-008**: Users MUST be able to view, for a selected asset and time horizon, the final indicator along with a human-readable explanation of how trust scores and school-level contributions produced that indicator.
- **FR-009**: System MUST provide a minimal interface or output format that allows users to switch between assets and time horizons without requiring any account creation or complex configuration.
- **FR-010**: System MUST operate in a way that supports transparent auditing of the trust score methodology, including the ability to trace an indicator back to underlying sentiments and performance evaluations.

### Key Entities *(include if feature involves data)*

- **Influencer**: Represents a person or account whose market commentary is analyzed. Key attributes include identifier/handle, assigned finance school(s), trust score history, and current trust score.
- **Tweet Sentiment**: Represents a single extracted sentiment from an influencer tweet. Key attributes include influencer reference, asset (BTC, Gold, S&P 500), direction (buy, neutral, sell), time horizon (short, medium, long), extraction timestamp, and confidence level.
- **Asset**: Represents a financial asset tracked by the system (BTC, Gold, S&P 500). Key attributes include symbol, name, and references to associated price time series.
- **Price Movement Window**: Represents the observed price performance of an asset over a specific time window following a sentiment timestamp. Key attributes include asset reference, window type (short, medium, long), start and end timestamps, and measured return or direction.
- **Trust Score**: Represents the calibrated performance score for an influencer, potentially per asset and horizon. Key attributes include influencer reference, calculation method reference, current score value, and history of updates.
- **Finance School**: Represents a conceptual finance theory school or worldview (e.g., macro-focused, technical analysis, value investing). Key attributes include name, description, and associated influencers.
- **Aggregated Signal**: Represents the aggregated, trust-weighted sentiment for an asset and horizon at a given point in time, at both school level and overall. Key attributes include asset, horizon, school (optional), aggregated score, and derived Buy / Neutral / Sell label.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of BTC, Gold, and the S&P 500, users can obtain a Buy / Neutral / Sell indicator for all three time horizons (short, medium, long) in a single interaction without needing to configure accounts or advanced settings.
- **SC-002**: At least 80% of indicators displayed include a traceable explanation that links the final label to underlying influencer trust scores, sentiment counts, and finance school contributions.
- **SC-003**: In a backtest over a representative historical period, indicators based on high-trust influencers demonstrate a statistically meaningful improvement in directional accuracy over unweighted sentiment (e.g., higher proportion of correct Buy/Sell outcomes compared to a naive baseline).
- **SC-004**: At least 90% of users in early tests report that they understand, at a high level, why a given indicator is Buy, Neutral, or Sell after viewing the explanation, indicating sufficient transparency and data-driven trust.

## Clarifications

### Session 2025-11-30

- Q: What is the expected scale of data ingestion? → A: Large: 50+ influencers, 10,000+ tweets/month
- Q: What time window should be used for trust score calculation? → A: All historical data
- Q: When there's insufficient data for an indicator, what should the system display? → A: Show "N/A" or "No data available"
- Q: When external APIs (X API, price data) fail or are rate-limited, how should the system behave? → A: Use cached data and show "last updated" timestamp
- Q: How frequently should trust scores be recalculated? → A: Weekly batch job

### Non-Functional Requirements

- **NFR-001**: System MUST handle large-scale data ingestion (50+ influencers, 10,000+ tweets/month).
- **NFR-002**: Trust scores MUST be calculated using all historical data available for each influencer.
- **NFR-003**: When insufficient data exists for an indicator, system MUST display "N/A" or "No data available" message.
- **NFR-004**: When external APIs fail or are rate-limited, system MUST use cached data and display "last updated" timestamp to users.
- **NFR-005**: Trust scores MUST be recalculated via weekly batch job.

### Edge Cases (Updated)

- **EC-001**: When there is insufficient tweet or price data for a given asset, horizon, or influencer, system displays "N/A" or "No data available" message.
- **EC-002**: When external APIs (X API, price data) fail or are rate-limited, system uses cached data and shows "last updated" timestamp.
- **EC-003**: How does the system handle conflicting sentiment signals (e.g., highly trusted influencers disagree on direction within the same horizon)?
- **EC-004**: What happens when a tweet's time horizon cannot be reliably extracted or is ambiguous?
- **EC-005**: How does the system handle influencers who change their handle or become inactive for long periods?


