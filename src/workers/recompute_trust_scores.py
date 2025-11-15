"""Backfill/recompute trust scores from existing prediction outcomes."""
import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import select, delete

from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, TrustScore
from src.services.logging import setup_logging, logger
from src.services.trust_scoring import compute_trust_scores_for_influencer


async def recompute_all_trust_scores(
    window_days: int = 180,
    clear_existing: bool = False
):
    """
    Recompute trust scores for all influencers from scratch.
    
    Useful for:
    - Initial backfill after adding historical data
    - Experimenting with different scoring algorithms
    - Fixing incorrect scores
    
    Args:
        window_days: Days of history to consider for scoring
        clear_existing: If True, delete all existing trust scores first
    """
    setup_logging()
    logger.info(f"Starting trust score recomputation (window={window_days} days)")
    
    async with AsyncSessionLocal() as session:
        # Optionally clear existing scores
        if clear_existing:
            logger.warning("Clearing all existing trust scores")
            await session.execute(delete(TrustScore))
            await session.commit()
            logger.info("✓ Existing scores cleared")
        
        # Get all influencers
        result = await session.execute(select(Influencer))
        influencers = result.scalars().all()
        
        if not influencers:
            logger.warning("No influencers found")
            return
        
        logger.info(f"Recomputing trust scores for {len(influencers)} influencers")
        
        total_scores = 0
        for influencer in influencers:
            logger.info(f"Computing scores for {influencer.handle}")
            
            # Compute new trust scores
            new_scores = await compute_trust_scores_for_influencer(
                session,
                influencer.id,
                window_days=window_days
            )
            
            # Save to database
            for score in new_scores:
                session.add(score)
            
            await session.commit()
            
            total_scores += len(new_scores)
            logger.info(f"  ✓ Computed {len(new_scores)} scores for {influencer.handle}")
        
        logger.info(f"✅ Recomputation complete - {total_scores} trust scores computed")
        logger.info(f"Influencers processed: {len(influencers)}")


async def recompute_influencer_trust_score(
    influencer_handle: str,
    window_days: int = 180
):
    """
    Recompute trust scores for a single influencer.
    
    Args:
        influencer_handle: X handle of the influencer
        window_days: Days of history to consider
    """
    setup_logging()
    logger.info(f"Recomputing trust scores for @{influencer_handle}")
    
    async with AsyncSessionLocal() as session:
        # Find influencer
        result = await session.execute(
            select(Influencer).where(Influencer.handle == influencer_handle)
        )
        influencer = result.scalar_one_or_none()
        
        if not influencer:
            logger.error(f"Influencer @{influencer_handle} not found")
            return
        
        # Delete existing scores for this influencer
        await session.execute(
            delete(TrustScore).where(TrustScore.influencer_id == influencer.id)
        )
        
        # Compute new scores
        new_scores = await compute_trust_scores_for_influencer(
            session,
            influencer.id,
            window_days=window_days
        )
        
        # Save to database
        for score in new_scores:
            session.add(score)
        
        await session.commit()
        
        logger.info(f"✅ Computed {len(new_scores)} trust scores for @{influencer_handle}")
        
        # Display summary
        for score in new_scores:
            asset_str = score.asset_symbol if score.asset_symbol else "OVERALL"
            logger.info(f"  {asset_str}/{score.horizon.value}: {score.score:.2f}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Recompute for specific influencer
        handle = sys.argv[1]
        asyncio.run(recompute_influencer_trust_score(handle))
    else:
        # Recompute for all
        asyncio.run(recompute_all_trust_scores())

