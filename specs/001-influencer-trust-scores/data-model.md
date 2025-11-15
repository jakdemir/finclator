# Data Model: Finclator Influencer Trust-Scoring MVP

## Overview

The data model supports ingestion of tweets, extraction of structured sentiments, storage of price history, evaluation of prediction outcomes, maintenance of influencer trust scores, finance school grouping, and computation of current signals per asset and horizon.

## Entities

### Influencer

- **id**: UUID (primary key)  
- **handle**: string (unique, current X handle)  
- **display_name**: string  
- **finance_school_id**: UUID (FK → FinanceSchool)  
- **created_at**: timestamp  
- **updated_at**: timestamp  

### FinanceSchool

- **id**: UUID (primary key)  
- **name**: string (e.g., "Macro", "Technical", "Value")  
- **description**: text  
- **created_at**: timestamp  
- **updated_at**: timestamp  

### Tweet

- **id**: UUID (primary key)  
- **influencer_id**: UUID (FK → Influencer)  
- **tweet_id**: string (X API identifier, unique)  
- **text**: text (normalized tweet content)  
- **tweeted_at**: timestamp (original tweet time)  
- **asset_symbols**: array(string) (e.g., ["BTC"], ["GOLD", "SPX"])  
- **ingested_at**: timestamp  
- **processed_for_sentiment**: boolean (default false)  

### SentimentPrediction

- **id**: UUID (primary key)  
- **tweet_id**: UUID (FK → Tweet)  
- **asset_symbol**: string (one of "BTC", "GOLD", "SPX")  
- **direction**: enum("BUY", "NEUTRAL", "SELL")  
- **horizon**: enum("SHORT", "MEDIUM", "LONG")  
- **model_version**: string (e.g., "grok-3-mini@v1")  
- **confidence**: numeric (0–1)  
- **created_at**: timestamp  
- **matures_at**: timestamp (end of the evaluation window for this prediction)  
- **evaluated**: boolean (default false)

### PriceCandle

- **id**: UUID (primary key)  
- **asset_symbol**: string (one of "BTC", "GOLD", "SPX")  
- **timestamp**: timestamp (candle open time)  
- **open**: numeric  
- **high**: numeric  
- **low**: numeric  
- **close**: numeric  
- **volume**: numeric (if available)  
- **source**: string (e.g., "AlphaVantage")  

### PredictionOutcome

- **id**: UUID (primary key)  
- **sentiment_prediction_id**: UUID (FK → SentimentPrediction)  
- **asset_symbol**: string  
- **horizon**: enum("SHORT", "MEDIUM", "LONG")  
- **entry_price**: numeric  
- **exit_price**: numeric  
- **return_pct**: numeric  
- **outcome**: enum("CORRECT", "WRONG", "UNCLEAR")  
- **evaluated_at**: timestamp  
- **evaluation_notes**: text (optional explanation or flags)

### TrustScore

- **id**: UUID (primary key)  
- **influencer_id**: UUID (FK → Influencer)  
- **asset_symbol**: string (nullable; null = overall across assets)  
- **horizon**: enum("SHORT", "MEDIUM", "LONG", "OVERALL")  
- **score**: numeric (e.g., 0–1 or log-odds style)  
- **window_start**: timestamp (start of performance window considered)  
- **window_end**: timestamp (end of performance window considered)  
- **computed_at**: timestamp  

### CurrentSignal

- **id**: UUID (primary key)  
- **asset_symbol**: string (one of "BTC", "GOLD", "SPX")  
- **horizon**: enum("SHORT", "MEDIUM", "LONG")  
- **finance_school_id**: UUID (nullable; null = overall aggregated across schools)  
- **weighted_score_buy**: numeric  
- **weighted_score_neutral**: numeric  
- **weighted_score_sell**: numeric  
- **final_label**: enum("BUY", "NEUTRAL", "SELL")  
- **generated_at**: timestamp  

## Key Relationships

- Influencer 1–N Tweet  
- Influencer N–1 FinanceSchool  
- Tweet 1–N SentimentPrediction  
- SentimentPrediction 1–1 PredictionOutcome  
- Influencer 1–N TrustScore  
- FinanceSchool 1–N Influencer  
- CurrentSignal entries exist per (asset_symbol, horizon) for each finance school and an overall row per combination.


