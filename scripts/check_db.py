"""Check database state for Sant Manukyan."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet, SentimentPrediction, PredictionOutcome, TrustScore


async def check():
    async with AsyncSessionLocal() as session:
        # Find influencer
        result = await session.execute(
            select(Influencer).where(Influencer.handle == "SantManukyan")
        )
        influencer = result.scalar_one_or_none()
        
        if not influencer:
            print("❌ Sant Manukyan not found in database")
            return
        
        print(f"✓ Influencer: @{influencer.handle} (ID: {influencer.id})")
        print()
        
        # Count tweets
        result = await session.execute(
            select(func.count(Tweet.id)).where(Tweet.influencer_id == influencer.id)
        )
        tweet_count = result.scalar() or 0
        print(f"Tweets: {tweet_count}")
        
        # Count predictions
        result = await session.execute(
            select(func.count(SentimentPrediction.id))
            .join(Tweet)
            .where(Tweet.influencer_id == influencer.id)
        )
        pred_count = result.scalar() or 0
        print(f"Predictions: {pred_count}")
        
        # Count outcomes
        result = await session.execute(
            select(func.count(PredictionOutcome.id))
            .join(SentimentPrediction)
            .join(Tweet)
            .where(Tweet.influencer_id == influencer.id)
        )
        outcome_count = result.scalar() or 0
        print(f"Outcomes: {outcome_count}")
        
        # Count trust scores
        result = await session.execute(
            select(func.count(TrustScore.id)).where(TrustScore.influencer_id == influencer.id)
        )
        score_count = result.scalar() or 0
        print(f"Trust Scores: {score_count}")
        
        if score_count > 0:
            print()
            print("Trust Scores:")
            result = await session.execute(
                select(TrustScore)
                .where(TrustScore.influencer_id == influencer.id)
                .order_by(TrustScore.asset_symbol.nullsfirst(), TrustScore.horizon)
            )
            for score in result.scalars().all():
                asset_str = score.asset_symbol if score.asset_symbol else "OVERALL"
                print(f"  {asset_str}/{score.horizon.value}: {score.score:.4f}")


if __name__ == "__main__":
    asyncio.run(check())

