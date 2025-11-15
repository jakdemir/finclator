"""Price ingestion worker - fetches OHLCV data for tracked assets."""
import asyncio
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from src.db.session import AsyncSessionLocal
from src.db.models import PriceCandle
from src.services.price_provider import price_provider
from src.services.logging import setup_logging, logger


TRACKED_ASSETS = ["BTC", "GOLD", "SPX"]


async def ingest_prices():
    """Main price ingestion logic - fetch and store OHLCV candles."""
    setup_logging()
    logger.info("Starting price ingestion worker")
    
    async with AsyncSessionLocal() as session:
        total_new = 0
        
        for asset_symbol in TRACKED_ASSETS:
            logger.info(f"Fetching price data for {asset_symbol}")
            
            try:
                # Fetch daily candles (compact = last 100 days)
                candles = await price_provider.fetch_daily_candles(
                    asset_symbol, outputsize="compact"
                )
                
                if not candles:
                    logger.warning(f"No price data returned for {asset_symbol}")
                    continue
                
                # Upsert candles (on conflict update close/high/low)
                for candle in candles:
                    stmt = insert(PriceCandle).values(
                        asset_symbol=candle["asset_symbol"],
                        timestamp=candle["timestamp"],
                        open=candle["open"],
                        high=candle["high"],
                        low=candle["low"],
                        close=candle["close"],
                        volume=candle.get("volume"),
                        source=candle["source"],
                    ).on_conflict_do_update(
                        index_elements=["asset_symbol", "timestamp"],
                        set_={
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                            "volume": candle.get("volume"),
                        },
                    )
                    
                    result = await session.execute(stmt)
                    if result.rowcount > 0:
                        total_new += 1
                
                await session.commit()
                logger.info(f"Ingested {len(candles)} candles for {asset_symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching prices for {asset_symbol}: {e}")
                await session.rollback()
        
        logger.info(f"Price ingestion complete - {total_new} candles upserted")


if __name__ == "__main__":
    asyncio.run(ingest_prices())

