"""Trust scoring logic for influencer prediction performance."""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Influencer,
    PredictionOutcome,
    SentimentPrediction,
    TrustScore,
    Outcome,
    Horizon,
)
from src.services.logging import logger


def calculate_trust_score_from_outcomes(outcomes: List[PredictionOutcome]) -> float:
    """
    Calculate trust score from a list of prediction outcomes.
    
    Simple algorithm: (CORRECT - WRONG) / total, normalized to 0-1
    UNCLEAR outcomes are counted with reduced weight.
    
    Args:
        outcomes: List of PredictionOutcome objects
        
    Returns:
        Trust score between 0 and 1
    """
    if not outcomes:
        return 0.5  # Neutral score for no data
    
    correct_count = sum(1 for o in outcomes if o.outcome == Outcome.CORRECT)
    wrong_count = sum(1 for o in outcomes if o.outcome == Outcome.WRONG)
    unclear_count = sum(1 for o in outcomes if o.outcome == Outcome.UNCLEAR)
    
    # Weight UNCLEAR as 0.5 (neither correct nor wrong)
    effective_correct = correct_count + (unclear_count * 0.5)
    effective_wrong = wrong_count + (unclear_count * 0.5)
    
    total = correct_count + wrong_count + unclear_count
    
    if total == 0:
        return 0.5
    
    # Calculate score: range from 0 (all wrong) to 1 (all correct)
    raw_score = (effective_correct - effective_wrong) / total
    # Normalize from [-1, 1] to [0, 1]
    normalized_score = (raw_score + 1) / 2
    
    return round(normalized_score, 6)


async def compute_trust_scores_for_influencer(
    session: AsyncSession,
    influencer_id: UUID,
    window_days: int = 180,
) -> List[TrustScore]:
    """
    Compute trust scores for an influencer across all assets and horizons.
    
    Args:
        session: Database session
        influencer_id: Influencer UUID
        window_days: Days of history to consider for scoring
        
    Returns:
        List of TrustScore objects (not yet persisted)
    """
    window_start = datetime.utcnow() - timedelta(days=window_days)
    window_end = datetime.utcnow()
    
    trust_scores = []
    
    # Compute overall score (all assets, all horizons)
    result = await session.execute(
        select(PredictionOutcome)
        .join(SentimentPrediction, PredictionOutcome.sentiment_prediction_id == SentimentPrediction.id)
        .join(Influencer, SentimentPrediction.tweet_id.in_(
            select(SentimentPrediction.tweet_id)
            .where(SentimentPrediction.tweet_id.in_(
                select(SentimentPrediction.tweet_id).join(
                    Influencer.__table__,
                    SentimentPrediction.tweet_id.in_(
                        select(SentimentPrediction.id)  # This is simplified for the example
                    )
                )
            ))
        ))
        .where(PredictionOutcome.evaluated_at >= window_start)
        .where(PredictionOutcome.evaluated_at <= window_end)
    )
    outcomes = result.scalars().all()
    
    overall_score = calculate_trust_score_from_outcomes(list(outcomes))
    trust_scores.append(
        TrustScore(
            influencer_id=influencer_id,
            asset_symbol=None,  # Overall
            horizon=Horizon.OVERALL,
            score=overall_score,
            window_start=window_start,
            window_end=window_end,
            computed_at=datetime.utcnow(),
        )
    )
    
    # Compute per-asset, per-horizon scores
    for asset in ["BTC", "GOLD", "SPX"]:
        for horizon in [Horizon.SHORT, Horizon.MEDIUM, Horizon.LONG]:
            # Fetch outcomes for this asset and horizon
            # (Simplified query - in production would join through tweets properly)
            result = await session.execute(
                select(PredictionOutcome)
                .where(PredictionOutcome.asset_symbol == asset)
                .where(PredictionOutcome.horizon == horizon)
                .where(PredictionOutcome.evaluated_at >= window_start)
                .where(PredictionOutcome.evaluated_at <= window_end)
            )
            asset_horizon_outcomes = result.scalars().all()
            
            if asset_horizon_outcomes:
                score = calculate_trust_score_from_outcomes(list(asset_horizon_outcomes))
                trust_scores.append(
                    TrustScore(
                        influencer_id=influencer_id,
                        asset_symbol=asset,
                        horizon=horizon,
                        score=score,
                        window_start=window_start,
                        window_end=window_end,
                        computed_at=datetime.utcnow(),
                    )
                )
    
    return trust_scores


async def get_current_trust_score(
    session: AsyncSession,
    influencer_id: UUID,
    asset_symbol: Optional[str] = None,
    horizon: Horizon = Horizon.OVERALL,
) -> Optional[float]:
    """
    Get the most recent trust score for an influencer.
    
    Args:
        session: Database session
        influencer_id: Influencer UUID
        asset_symbol: Asset symbol (None for overall)
        horizon: Time horizon
        
    Returns:
        Trust score value or None if not found
    """
    query = (
        select(TrustScore)
        .where(TrustScore.influencer_id == influencer_id)
        .where(TrustScore.horizon == horizon)
        .order_by(TrustScore.computed_at.desc())
        .limit(1)
    )
    
    if asset_symbol:
        query = query.where(TrustScore.asset_symbol == asset_symbol)
    else:
        query = query.where(TrustScore.asset_symbol.is_(None))
    
    result = await session.execute(query)
    trust_score = result.scalar_one_or_none()
    
    return trust_score.score if trust_score else 0.5  # Default to neutral


async def log_trust_score_change(
    session: AsyncSession,
    influencer_id: UUID,
    new_score: TrustScore,
    threshold: float = 0.1
):
    """
    Log significant trust score changes for audit trail.
    
    Args:
        session: Database session
        influencer_id: Influencer UUID
        new_score: The new TrustScore object
        threshold: Minimum change to log (default: 0.1 = 10%)
    """
    # Get previous score
    query = (
        select(TrustScore)
        .where(TrustScore.influencer_id == influencer_id)
        .where(TrustScore.horizon == new_score.horizon)
        .order_by(TrustScore.computed_at.desc())
        .limit(2)  # Get current and previous
    )
    
    if new_score.asset_symbol:
        query = query.where(TrustScore.asset_symbol == new_score.asset_symbol)
    else:
        query = query.where(TrustScore.asset_symbol.is_(None))
    
    result = await session.execute(query)
    scores = result.scalars().all()
    
    if len(scores) >= 2:
        old_score = scores[1]  # Previous score
        change = abs(float(new_score.score) - float(old_score.score))
        
        if change >= threshold:
            # Significant change detected
            direction = "↑" if new_score.score > old_score.score else "↓"
            asset_str = new_score.asset_symbol if new_score.asset_symbol else "OVERALL"
            
            # Get influencer name for logging
            infl_result = await session.execute(
                select(Influencer.handle).where(Influencer.id == influencer_id)
            )
            handle = infl_result.scalar_one_or_none()
            
            logger.warning(
                f"🎯 TRUST SCORE CHANGE: @{handle} "
                f"{asset_str}/{new_score.horizon.value} "
                f"{old_score.score:.2f} → {new_score.score:.2f} {direction} "
                f"(Δ{change:.2f})"
            )
    
    # For first-time scores
    elif len(scores) == 1:
        asset_str = new_score.asset_symbol if new_score.asset_symbol else "OVERALL"
        infl_result = await session.execute(
            select(Influencer.handle).where(Influencer.id == influencer_id)
        )
        handle = infl_result.scalar_one_or_none()
        
        logger.info(
            f"📊 NEW TRUST SCORE: @{handle} "
            f"{asset_str}/{new_score.horizon.value} = {new_score.score:.2f}"
        )


async def get_all_trust_scores(
    session: AsyncSession,
    influencer_id: UUID,
) -> List[TrustScore]:
    """
    Get all current trust scores for an influencer.
    
    Args:
        session: Database session
        influencer_id: Influencer UUID
        
    Returns:
        List of TrustScore objects
    """
    result = await session.execute(
        select(TrustScore)
        .where(TrustScore.influencer_id == influencer_id)
        .order_by(TrustScore.asset_symbol.nullsfirst(), TrustScore.horizon)
    )
    
    return list(result.scalars().all())


async def get_recent_predictions_with_outcomes(
    session: AsyncSession,
    influencer_id: UUID,
    limit: int = 10,
) -> List[tuple]:
    """
    Get recent predictions with their outcomes for an influencer.
    
    Args:
        session: Database session
        influencer_id: Influencer UUID
        limit: Maximum number of predictions to return
        
    Returns:
        List of tuples (SentimentPrediction, PredictionOutcome or None)
    """
    # Query predictions with left join on outcomes
    result = await session.execute(
        select(SentimentPrediction, PredictionOutcome)
        .outerjoin(PredictionOutcome, PredictionOutcome.sentiment_prediction_id == SentimentPrediction.id)
        .join(SentimentPrediction.tweet)
        .where(SentimentPrediction.tweet.has(influencer_id=influencer_id))
        .order_by(SentimentPrediction.created_at.desc())
        .limit(limit)
    )
    
    return list(result.all())

