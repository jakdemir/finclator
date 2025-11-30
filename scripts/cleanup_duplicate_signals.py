"""Clean up duplicate CurrentSignal records, keeping only the most recent."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, delete
from src.db.session import AsyncSessionLocal
from src.db.models import CurrentSignal
from src.services.logging import setup_logging, logger


async def cleanup_duplicates():
    """Remove duplicate signals, keeping only the most recent for each asset/horizon/school combination."""
    setup_logging()
    logger.info("Starting duplicate signal cleanup...")
    
    async with AsyncSessionLocal() as session:
        # Find all duplicate combinations
        result = await session.execute(
            select(
                CurrentSignal.asset_symbol,
                CurrentSignal.horizon,
                CurrentSignal.finance_school_id,
                func.count(CurrentSignal.id).label('count'),
                func.max(CurrentSignal.generated_at).label('max_generated_at')
            )
            .group_by(
                CurrentSignal.asset_symbol,
                CurrentSignal.horizon,
                CurrentSignal.finance_school_id
            )
            .having(func.count(CurrentSignal.id) > 1)
        )
        duplicates = result.all()
        
        if not duplicates:
            logger.info("No duplicates found")
            return
        
        logger.info(f"Found {len(duplicates)} duplicate groups")
        
        total_deleted = 0
        for asset, horizon, school_id, count, max_generated_at in duplicates:
            logger.info(
                f"Cleaning {count} duplicates for {asset} {horizon.value} "
                f"(school_id={school_id}), keeping most recent ({max_generated_at})"
            )
            
            # Delete all except the most recent
            delete_stmt = delete(CurrentSignal).where(
                CurrentSignal.asset_symbol == asset,
                CurrentSignal.horizon == horizon,
                CurrentSignal.finance_school_id == school_id,
                CurrentSignal.generated_at < max_generated_at
            )
            result = await session.execute(delete_stmt)
            deleted = result.rowcount
            total_deleted += deleted
            logger.info(f"  Deleted {deleted} old records")
        
        await session.commit()
        logger.info(f"Cleanup complete: {total_deleted} duplicate records deleted")


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())

