"""Signal aggregation logic for computing Buy/Neutral/Sell indicators."""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    SentimentPrediction,
    TrustScore,
    Influencer,
    Tweet,
    Direction,
    Horizon,
    FinanceSchool,
)
from src.services.trust_scoring import get_current_trust_score
from src.services.logging import logger


async def aggregate_signals_for_asset_horizon(
    session: AsyncSession,
    asset_symbol: str,
    horizon: Horizon,
    finance_school_id: Optional[UUID] = None,
    lookback_days: int = 30,
) -> Tuple[float, float, float, Direction]:
    """
    Aggregate trust-weighted signals for an asset and horizon.
    
    Args:
        session: Database session
        asset_symbol: Asset symbol (BTC, GOLD, SPX)
        horizon: Time horizon
        finance_school_id: Optional finance school to filter by
        lookback_days: Days of recent predictions to consider
        
    Returns:
        Tuple of (weighted_buy, weighted_neutral, weighted_sell, final_label)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Build query for recent predictions
    query = (
        select(SentimentPrediction, Tweet, Influencer)
        .join(Tweet, SentimentPrediction.tweet_id == Tweet.id)
        .join(Influencer, Tweet.influencer_id == Influencer.id)
        .where(SentimentPrediction.asset_symbol == asset_symbol)
        .where(SentimentPrediction.horizon == horizon)
        .where(SentimentPrediction.created_at >= cutoff_date)
        .where(SentimentPrediction.evaluated == False)  # Only unfulfilled predictions
    )
    
    if finance_school_id:
        query = query.where(Influencer.finance_school_id == finance_school_id)
    
    result = await session.execute(query)
    predictions_with_context = result.all()
    
    if not predictions_with_context:
        # No predictions - return neutral
        return (0.0, 1.0, 0.0, Direction.NEUTRAL)
    
    # Accumulate weighted scores
    weighted_buy = 0.0
    weighted_neutral = 0.0
    weighted_sell = 0.0
    total_weight = 0.0
    
    for prediction, tweet, influencer in predictions_with_context:
        # Get influencer's trust score for this asset/horizon
        trust_score = await get_current_trust_score(
            session, influencer.id, asset_symbol, horizon
        )
        
        # Weight by trust score and confidence
        weight = trust_score * float(prediction.confidence)
        
        # Add to appropriate bucket
        if prediction.direction == Direction.BUY:
            weighted_buy += weight
        elif prediction.direction == Direction.NEUTRAL:
            weighted_neutral += weight
        else:  # SELL
            weighted_sell += weight
        
        total_weight += weight
    
    # Normalize scores
    if total_weight > 0:
        weighted_buy /= total_weight
        weighted_neutral /= total_weight
        weighted_sell /= total_weight
    else:
        # Fallback to neutral
        weighted_buy = 0.0
        weighted_neutral = 1.0
        weighted_sell = 0.0
    
    # Determine final label (highest weighted score)
    if weighted_buy > weighted_neutral and weighted_buy > weighted_sell:
        final_label = Direction.BUY
    elif weighted_sell > weighted_neutral and weighted_sell > weighted_buy:
        final_label = Direction.SELL
    else:
        final_label = Direction.NEUTRAL
    
    return (
        round(weighted_buy, 6),
        round(weighted_neutral, 6),
        round(weighted_sell, 6),
        final_label,
    )


async def get_all_finance_schools(session: AsyncSession) -> List[FinanceSchool]:
    """
    Get all finance schools from the database.
    
    Args:
        session: Database session
        
    Returns:
        List of FinanceSchool objects
    """
    result = await session.execute(select(FinanceSchool))
    return list(result.scalars().all())

