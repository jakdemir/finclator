"""Weekly batch job to recompute trust scores for all influencers."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, TrustScore
from src.services.trust_scoring import compute_trust_scores_for_influencer
from src.services.logging import setup_logging, logger


async def recompute_all_trust_scores():
    """
    Recompute trust scores for all influencers using all historical data.
    
    This is designed to run as a weekly batch job.
    """
    setup_logging()
    logger.info("Starting trust score recalculation for all influencers...")
    
    async with AsyncSessionLocal() as session:
        # Get all influencers
        result = await session.execute(select(Influencer))
        influencers = result.scalars().all()
        
        logger.info(f"Found {len(influencers)} influencers to process")
        
        processed = 0
        errors = 0
        
        for influencer in influencers:
            try:
                logger.info(f"Processing influencer: {influencer.handle} ({influencer.id})")
                
                # Compute trust scores using all historical data (window_days=None)
                new_scores = await compute_trust_scores_for_influencer(
                    session,
                    influencer.id,
                    window_days=None,  # All historical data per spec clarification
                )
                
                # Delete old scores for this influencer
                await session.execute(
                    select(TrustScore).where(TrustScore.influencer_id == influencer.id)
                )
                old_scores_result = await session.execute(
                    select(TrustScore).where(TrustScore.influencer_id == influencer.id)
                )
                old_scores = old_scores_result.scalars().all()
                for old_score in old_scores:
                    await session.delete(old_score)
                
                # Persist new scores
                for score in new_scores:
                    session.add(score)
                
                await session.commit()
                
                logger.info(
                    f"✓ Updated {len(new_scores)} trust scores for {influencer.handle}"
                )
                processed += 1
                
            except Exception as e:
                logger.error(f"✗ Failed to recompute scores for {influencer.handle}: {e}")
                await session.rollback()
                errors += 1
        
        logger.info(
            f"Trust score recalculation complete: {processed} processed, {errors} errors"
        )


if __name__ == "__main__":
    asyncio.run(recompute_all_trust_scores())

