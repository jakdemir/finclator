"""Signal aggregation service for computing trust-weighted indicators."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    CurrentSignal,
    SentimentPrediction,
    TrustScore,
    Influencer,
    FinanceSchool,
    Direction,
    Horizon,
)
from src.services.logging import logger


async def aggregate_signals(
    session: AsyncSession,
    asset_symbol: str,
    horizon: Horizon,
) -> List[CurrentSignal]:
    """
    Aggregate trust-weighted sentiment signals for an asset and horizon.
    
    Computes signals at both school-level and overall level, writing to CurrentSignal table.
    
    Args:
        session: Database session
        asset_symbol: Asset symbol (BTC, GOLD, SPX)
        horizon: Time horizon (SHORT, MEDIUM, LONG)
        
    Returns:
        List of CurrentSignal objects (persisted)
    """
    logger.info(f"Aggregating signals for {asset_symbol} {horizon.value}")
    
    # Get all finance schools
    schools_result = await session.execute(select(FinanceSchool))
    schools = schools_result.scalars().all()
    
    signals = []
    
    # Aggregate per finance school
    for school in schools:
        # Get influencers in this school
        influencers_result = await session.execute(
            select(Influencer).where(Influencer.finance_school_id == school.id)
        )
        influencers = influencers_result.scalars().all()
        
        if not influencers:
            continue
        
        # Aggregate sentiment predictions weighted by trust scores
        weighted_buy = 0.0
        weighted_neutral = 0.0
        weighted_sell = 0.0
        total_weight = 0.0
        
        for influencer in influencers:
            # Get trust score for this influencer, asset, horizon
            trust_result = await session.execute(
                select(TrustScore).where(
                    TrustScore.influencer_id == influencer.id,
                    TrustScore.asset_symbol == asset_symbol,
                    TrustScore.horizon == horizon,
                )
            )
            trust_score = trust_result.scalar_one_or_none()
            
            if not trust_score:
                # Try overall trust score (asset_symbol is None)
                trust_result = await session.execute(
                    select(TrustScore).where(
                        TrustScore.influencer_id == influencer.id,
                        TrustScore.asset_symbol.is_(None),
                        TrustScore.horizon == Horizon.OVERALL,
                    )
                )
                trust_score = trust_result.scalar_one_or_none()
            
            # Default trust score if none found (convert Decimal to float)
            trust_weight = float(trust_score.score) if trust_score else 0.5
            
            # Get recent sentiment predictions for this influencer and asset
            from src.db.models import Tweet
            predictions_result = await session.execute(
                select(SentimentPrediction)
                .join(Tweet, SentimentPrediction.tweet_id == Tweet.id)
                .where(
                    Tweet.influencer_id == influencer.id,
                    SentimentPrediction.asset_symbol == asset_symbol,
                    SentimentPrediction.horizon == horizon,
                )
                .order_by(SentimentPrediction.created_at.desc())
                .limit(100)  # Recent predictions only
            )
            predictions = predictions_result.scalars().all()
            
            for prediction in predictions:
                weight = float(trust_weight) * float(prediction.confidence)
                total_weight += weight
                
                if prediction.direction == Direction.BUY:
                    weighted_buy += weight
                elif prediction.direction == Direction.NEUTRAL:
                    weighted_neutral += weight
                elif prediction.direction == Direction.SELL:
                    weighted_sell += weight
        
        if total_weight == 0:
            continue
        
        # Normalize scores
        normalized_buy = weighted_buy / total_weight if total_weight > 0 else 0.0
        normalized_neutral = weighted_neutral / total_weight if total_weight > 0 else 0.0
        normalized_sell = weighted_sell / total_weight if total_weight > 0 else 0.0
        
        # Determine final label
        if normalized_buy > normalized_neutral and normalized_buy > normalized_sell:
            final_label = Direction.BUY
        elif normalized_sell > normalized_neutral and normalized_sell > normalized_buy:
            final_label = Direction.SELL
        else:
            final_label = Direction.NEUTRAL
        
        # Create or update CurrentSignal for this school
        # Delete any existing signals for this school first to avoid duplicates
        existing_result = await session.execute(
            select(CurrentSignal).where(
                CurrentSignal.asset_symbol == asset_symbol,
                CurrentSignal.horizon == horizon,
                CurrentSignal.finance_school_id == school.id,
            )
        )
        existing_signals = existing_result.scalars().all()
        for existing in existing_signals:
            await session.delete(existing)
        
        # Flush deletes before creating new signal
        await session.flush()
        
        # Create new signal for this school
        signal = CurrentSignal(
            asset_symbol=asset_symbol,
            horizon=horizon,
            finance_school_id=school.id,
            weighted_score_buy=normalized_buy,
            weighted_score_neutral=normalized_neutral,
            weighted_score_sell=normalized_sell,
            final_label=final_label,
            generated_at=datetime.utcnow(),
        )
        session.add(signal)
        signals.append(signal)
    
    # Aggregate overall (across all schools)
    # Sum up all school-level signals (convert Decimal to float)
    overall_buy = sum(float(s.weighted_score_buy) for s in signals)
    overall_neutral = sum(float(s.weighted_score_neutral) for s in signals)
    overall_sell = sum(float(s.weighted_score_sell) for s in signals)
    total = overall_buy + overall_neutral + overall_sell
    
    if total > 0:
        normalized_buy = overall_buy / total
        normalized_neutral = overall_neutral / total
        normalized_sell = overall_sell / total
        
        if normalized_buy > normalized_neutral and normalized_buy > normalized_sell:
            final_label = Direction.BUY
        elif normalized_sell > normalized_neutral and normalized_sell > normalized_buy:
            final_label = Direction.SELL
        else:
            final_label = Direction.NEUTRAL
        
        # Create or update overall signal (finance_school_id is None)
        # Delete any existing overall signals first to avoid duplicates
        existing_result = await session.execute(
            select(CurrentSignal).where(
                CurrentSignal.asset_symbol == asset_symbol,
                CurrentSignal.horizon == horizon,
                CurrentSignal.finance_school_id.is_(None),
            )
        )
        existing_signals = existing_result.scalars().all()
        for existing in existing_signals:
            await session.delete(existing)
        
        # Flush deletes before creating new signal
        await session.flush()
        
        # Create new overall signal
        signal = CurrentSignal(
            asset_symbol=asset_symbol,
            horizon=horizon,
            finance_school_id=None,
            weighted_score_buy=normalized_buy,
            weighted_score_neutral=normalized_neutral,
            weighted_score_sell=normalized_sell,
            final_label=final_label,
            generated_at=datetime.utcnow(),
        )
        session.add(signal)
        signals.append(signal)
    
    await session.commit()
    logger.info(f"Generated {len(signals)} signals for {asset_symbol} {horizon.value}")
    
    return signals

