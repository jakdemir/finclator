"""Worker script to aggregate signals and populate CurrentSignal table."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from src.db.session import AsyncSessionLocal
from src.db.models import Horizon
from src.services.signal_aggregator import aggregate_signals
from src.services.logging import setup_logging, logger


async def run_aggregation():
    """Aggregate signals for all assets and horizons."""
    setup_logging()
    
    assets = ["BTC", "GOLD", "SPX"]
    horizons = [Horizon.SHORT, Horizon.MEDIUM, Horizon.LONG]
    
    async with AsyncSessionLocal() as session:
        for asset in assets:
            for horizon in horizons:
                try:
                    await aggregate_signals(session, asset, horizon)
                    logger.info(f"✓ Aggregated signals for {asset} {horizon.value}")
                except Exception as e:
                    logger.error(f"✗ Failed to aggregate {asset} {horizon.value}: {e}")
                    await session.rollback()
    
    logger.info("Signal aggregation complete")


if __name__ == "__main__":
    asyncio.run(run_aggregation())

