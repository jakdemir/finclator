"""Evaluation worker - computes prediction outcomes and updates trust scores."""
import asyncio
from datetime import datetime

from sqlalchemy import select, and_

from src.db.session import AsyncSessionLocal
from src.db.models import (
    SentimentPrediction,
    PredictionOutcome,
    PriceCandle,
    TrustScore,
    Outcome,
    Direction,
    Tweet,
)
from src.services.trust_scoring import compute_trust_scores_for_influencer
from src.services.logging import setup_logging, logger, log_evaluation


def determine_outcome(
    predicted_direction: Direction, entry_price: float, exit_price: float, threshold: float = 0.02
) -> Outcome:
    """
    Determine if a prediction was CORRECT, WRONG, or UNCLEAR.
    
    Args:
        predicted_direction: BUY, NEUTRAL, or SELL
        entry_price: Price at prediction time
        exit_price: Price at maturity time
        threshold: Minimum % move to count as directional (default 2%)
        
    Returns:
        Outcome enum
    """
    return_pct = ((exit_price - entry_price) / entry_price) * 100
    
    # Determine actual market direction
    if abs(return_pct) < threshold:
        actual_direction = Direction.NEUTRAL
    elif return_pct > 0:
        actual_direction = Direction.BUY  # Market went up
    else:
        actual_direction = Direction.SELL  # Market went down
    
    # Compare prediction with actual
    if predicted_direction == actual_direction:
        return Outcome.CORRECT
    elif predicted_direction == Direction.NEUTRAL or actual_direction == Direction.NEUTRAL:
        return Outcome.UNCLEAR  # Neutral predictions are ambiguous
    else:
        return Outcome.WRONG


async def evaluate_predictions():
    """Main evaluation logic - compute outcomes for matured predictions."""
    setup_logging()
    logger.info("Starting prediction evaluation worker")
    
    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        
        # Get matured predictions that haven't been evaluated
        result = await session.execute(
            select(SentimentPrediction, Tweet)
            .join(Tweet, SentimentPrediction.tweet_id == Tweet.id)
            .where(SentimentPrediction.evaluated == False)
            .where(SentimentPrediction.matures_at <= now)
            .limit(100)
        )
        predictions_with_tweets = result.all()
        
        if not predictions_with_tweets:
            logger.info("No matured predictions to evaluate")
            return
        
        logger.info(f"Evaluating {len(predictions_with_tweets)} matured predictions")
        
        evaluated_count = 0
        influencers_to_update = set()
        
        for prediction, tweet in predictions_with_tweets:
            try:
                # Get entry price (close price on tweet date)
                entry_result = await session.execute(
                    select(PriceCandle)
                    .where(PriceCandle.asset_symbol == prediction.asset_symbol)
                    .where(PriceCandle.timestamp >= tweet.tweeted_at)
                    .order_by(PriceCandle.timestamp.asc())
                    .limit(1)
                )
                entry_candle = entry_result.scalar_one_or_none()
                
                if not entry_candle:
                    logger.warning(
                        f"No entry price found for prediction {prediction.id} "
                        f"(asset: {prediction.asset_symbol}, date: {tweet.tweeted_at})"
                    )
                    continue
                
                # Get exit price (close price on maturity date)
                exit_result = await session.execute(
                    select(PriceCandle)
                    .where(PriceCandle.asset_symbol == prediction.asset_symbol)
                    .where(PriceCandle.timestamp >= prediction.matures_at)
                    .order_by(PriceCandle.timestamp.asc())
                    .limit(1)
                )
                exit_candle = exit_result.scalar_one_or_none()
                
                if not exit_candle:
                    logger.warning(
                        f"No exit price found for prediction {prediction.id} "
                        f"(asset: {prediction.asset_symbol}, maturity: {prediction.matures_at})"
                    )
                    continue
                
                # Calculate outcome
                entry_price = float(entry_candle.close)
                exit_price = float(exit_candle.close)
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                
                outcome = determine_outcome(prediction.direction, entry_price, exit_price)
                
                # Create PredictionOutcome
                prediction_outcome = PredictionOutcome(
                    sentiment_prediction_id=prediction.id,
                    asset_symbol=prediction.asset_symbol,
                    horizon=prediction.horizon,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    return_pct=return_pct,
                    outcome=outcome,
                    evaluated_at=now,
                    evaluation_notes=None,
                )
                
                session.add(prediction_outcome)
                
                # Mark prediction as evaluated
                prediction.evaluated = True
                
                log_evaluation(
                    str(prediction.id),
                    prediction.asset_symbol,
                    outcome.value,
                    entry_price,
                    exit_price,
                    return_pct,
                )
                
                # Track influencer for trust score update
                influencers_to_update.add(tweet.influencer_id)
                
                evaluated_count += 1
                
            except Exception as e:
                logger.error(f"Error evaluating prediction {prediction.id}: {e}")
                continue
        
        await session.commit()
        
        # Update trust scores for affected influencers
        logger.info(f"Updating trust scores for {len(influencers_to_update)} influencers")
        
        for influencer_id in influencers_to_update:
            try:
                trust_scores = await compute_trust_scores_for_influencer(
                    session, influencer_id
                )
                
                for trust_score in trust_scores:
                    session.add(trust_score)
                
                await session.commit()
                logger.info(f"Updated trust scores for influencer {influencer_id}")
                
            except Exception as e:
                logger.error(f"Error updating trust scores for {influencer_id}: {e}")
                await session.rollback()
        
        logger.info(
            f"Evaluation complete - {evaluated_count} predictions evaluated, "
            f"{len(influencers_to_update)} influencers updated"
        )


if __name__ == "__main__":
    asyncio.run(evaluate_predictions())

