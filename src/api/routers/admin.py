"""Admin API endpoints for database inspection and monitoring."""
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    FinanceSchool, Influencer, Tweet, SentimentPrediction,
    PriceCandle, PredictionOutcome, TrustScore, CurrentSignal
)
from src.api.dependencies import get_db_session


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_database_stats(session: AsyncSession = Depends(get_db_session)):
    """Get database statistics and row counts."""
    
    tables = [
        ("finance_schools", FinanceSchool),
        ("influencers", Influencer),
        ("tweets", Tweet),
        ("sentiment_predictions", SentimentPrediction),
        ("price_candles", PriceCandle),
        ("prediction_outcomes", PredictionOutcome),
        ("trust_scores", TrustScore),
        ("current_signals", CurrentSignal),
    ]
    
    stats = {}
    for table_name, model in tables:
        result = await session.execute(select(func.count()).select_from(model))
        count = result.scalar()
        stats[table_name] = count
    
    # Additional stats
    # Tweets by asset
    btc_tweets = await session.execute(
        select(func.count(Tweet.id)).where(Tweet.asset_symbols.contains(["BTC"]))
    )
    gold_tweets = await session.execute(
        select(func.count(Tweet.id)).where(Tweet.asset_symbols.contains(["GOLD"]))
    )
    spx_tweets = await session.execute(
        select(func.count(Tweet.id)).where(Tweet.asset_symbols.contains(["SPX"]))
    )
    
    # Processed tweets
    processed = await session.execute(
        select(func.count(Tweet.id)).where(Tweet.processed_for_sentiment == True)
    )
    
    stats["tweets_by_asset"] = {
        "BTC": btc_tweets.scalar(),
        "GOLD": gold_tweets.scalar(),
        "SPX": spx_tweets.scalar(),
    }
    stats["tweets_processed"] = processed.scalar()
    stats["tweets_pending"] = stats["tweets"] - stats["tweets_processed"]
    
    return stats


@router.get("/tweets")
async def get_recent_tweets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
):
    """Get recent tweets with influencer info."""
    
    result = await session.execute(
        select(Tweet, Influencer.handle, Influencer.display_name)
        .join(Influencer, Tweet.influencer_id == Influencer.id)
        .order_by(Tweet.tweeted_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    tweets_data = result.all()
    
    return [
        {
            "id": str(tweet.id),
            "tweet_id": tweet.tweet_id,
            "influencer_handle": handle,
            "influencer_name": name,
            "text": tweet.text,
            "asset_symbols": tweet.asset_symbols,
            "tweeted_at": tweet.tweeted_at.isoformat(),
            "processed": tweet.processed_for_sentiment,
        }
        for tweet, handle, name in tweets_data
    ]


@router.get("/predictions")
async def get_recent_predictions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session)
):
    """Get recent sentiment predictions."""
    
    result = await session.execute(
        select(SentimentPrediction, Tweet.text, Influencer.handle)
        .join(Tweet, SentimentPrediction.tweet_id == Tweet.id)
        .join(Influencer, Tweet.influencer_id == Influencer.id)
        .order_by(SentimentPrediction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    predictions_data = result.all()
    
    return [
        {
            "id": str(pred.id),
            "asset": pred.asset_symbol,
            "direction": pred.direction.value,
            "horizon": pred.horizon.value,
            "confidence": float(pred.confidence),
            "tweet_text": text[:100] + "..." if len(text) > 100 else text,
            "influencer": handle,
            "created_at": pred.created_at.isoformat(),
        }
        for pred, text, handle in predictions_data
    ]


@router.get("/price-candles")
async def get_recent_prices(
    asset: str = Query("BTC"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Get recent price candles for an asset."""
    
    result = await session.execute(
        select(PriceCandle)
        .where(PriceCandle.asset_symbol == asset)
        .order_by(PriceCandle.timestamp.desc())
        .limit(limit)
    )
    
    candles = result.scalars().all()
    
    return [
        {
            "asset": candle.asset_symbol,
            "timestamp": candle.timestamp.isoformat(),
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": float(candle.volume),
        }
        for candle in candles
    ]


@router.get("/trust-scores")
async def get_trust_scores(
    session: AsyncSession = Depends(get_db_session)
):
    """Get all current trust scores."""
    
    result = await session.execute(
        select(TrustScore, Influencer.handle, Influencer.display_name)
        .join(Influencer, TrustScore.influencer_id == Influencer.id)
        .order_by(TrustScore.computed_at.desc())
    )
    
    scores_data = result.all()
    
    return [
        {
            "influencer_handle": handle,
            "influencer_name": name,
            "asset": score.asset_symbol,
            "horizon": score.horizon.value,
            "score": float(score.score),
            "computed_at": score.computed_at.isoformat(),
        }
        for score, handle, name in scores_data
    ]


@router.get("/outcomes")
async def get_prediction_outcomes(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Get prediction outcomes."""
    
    result = await session.execute(
        select(PredictionOutcome, SentimentPrediction, Influencer.handle)
        .join(SentimentPrediction, PredictionOutcome.sentiment_prediction_id == SentimentPrediction.id)
        .join(Tweet, SentimentPrediction.tweet_id == Tweet.id)
        .join(Influencer, Tweet.influencer_id == Influencer.id)
        .order_by(PredictionOutcome.evaluated_at.desc())
        .limit(limit)
    )
    
    outcomes_data = result.all()
    
    return [
        {
            "influencer": handle,
            "asset": pred.asset_symbol,
            "horizon": pred.horizon.value,
            "predicted_direction": pred.direction.value,
            "outcome": outcome.outcome.value,
            "entry_price": float(outcome.entry_price),
            "exit_price": float(outcome.exit_price),
            "return_pct": float(outcome.return_pct),
            "evaluated_at": outcome.evaluated_at.isoformat(),
        }
        for outcome, pred, handle in outcomes_data
    ]


@router.get("/pipeline-status")
async def get_pipeline_status(session: AsyncSession = Depends(get_db_session)):
    """Get current pipeline processing status."""
    
    # Recent activity
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    
    # Tweets ingested in last 24h
    recent_tweets = await session.execute(
        select(func.count(Tweet.id))
        .where(Tweet.ingested_at >= last_24h)
    )
    
    # Predictions created in last 24h
    recent_predictions = await session.execute(
        select(func.count(SentimentPrediction.id))
        .where(SentimentPrediction.created_at >= last_24h)
    )
    
    # Price candles updated in last 24h
    recent_prices = await session.execute(
        select(func.count(PriceCandle.id))
        .where(PriceCandle.ingested_at >= last_24h)
    )
    
    # Signals updated in last 24h
    recent_signals = await session.execute(
        select(func.count(CurrentSignal.id))
        .where(CurrentSignal.generated_at >= last_24h)
    )
    
    # Latest timestamps
    latest_tweet = await session.execute(
        select(func.max(Tweet.ingested_at))
    )
    latest_prediction = await session.execute(
        select(func.max(SentimentPrediction.created_at))
    )
    latest_signal = await session.execute(
        select(func.max(CurrentSignal.generated_at))
    )
    
    return {
        "last_24_hours": {
            "tweets_ingested": recent_tweets.scalar() or 0,
            "predictions_created": recent_predictions.scalar() or 0,
            "price_candles_updated": recent_prices.scalar() or 0,
            "signals_updated": recent_signals.scalar() or 0,
        },
        "latest_activity": {
            "last_tweet_ingested": latest_tweet.scalar().isoformat() if latest_tweet.scalar() else None,
            "last_prediction": latest_prediction.scalar().isoformat() if latest_prediction.scalar() else None,
            "last_signal_update": latest_signal.scalar().isoformat() if latest_signal.scalar() else None,
        }
    }

