"""Clear tweet and sentiment data from database for fresh start."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select
from src.db.session import AsyncSessionLocal
from src.db.models import Tweet, SentimentPrediction, PredictionOutcome, TrustScore, CurrentSignal
from src.services.logging import setup_logging, logger


async def clear_tweet_data():
    """Clear all tweet-related data."""
    setup_logging()
    
    print("🗑️  Clearing tweet and sentiment data...")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        # Delete in order (respecting foreign keys)
        
        # 1. Delete current signals (independent, can be deleted first)
        result = await session.execute(delete(CurrentSignal))
        signals_deleted = result.rowcount
        logger.info(f"Deleted {signals_deleted} current signals")
        
        # 2. Delete trust scores (depend on outcomes)
        result = await session.execute(delete(TrustScore))
        trust_scores_deleted = result.rowcount
        logger.info(f"Deleted {trust_scores_deleted} trust scores")
        
        # 3. Delete prediction outcomes (depend on predictions)
        result = await session.execute(delete(PredictionOutcome))
        outcomes_deleted = result.rowcount
        logger.info(f"Deleted {outcomes_deleted} prediction outcomes")
        
        # 4. Delete sentiment predictions (depend on tweets)
        result = await session.execute(delete(SentimentPrediction))
        predictions_deleted = result.rowcount
        logger.info(f"Deleted {predictions_deleted} sentiment predictions")
        
        # 5. Delete tweets
        result = await session.execute(delete(Tweet))
        tweets_deleted = result.rowcount
        logger.info(f"Deleted {tweets_deleted} tweets")
        
        await session.commit()
        
        print()
        print("✅ Cleared data:")
        print(f"   Current Signals: {signals_deleted}")
        print(f"   Tweets: {tweets_deleted}")
        print(f"   Predictions: {predictions_deleted}")
        print(f"   Outcomes: {outcomes_deleted}")
        print(f"   Trust Scores: {trust_scores_deleted}")
        print()
        print("Database is now clean and ready for fresh data.")


if __name__ == "__main__":
    asyncio.run(clear_tweet_data())

