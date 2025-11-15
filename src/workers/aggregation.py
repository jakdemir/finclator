"""Aggregation worker - computes and stores current signals."""
import asyncio
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from src.db.session import AsyncSessionLocal
from src.db.models import CurrentSignal, Horizon
from src.services.signal_aggregator import (
    aggregate_signals_for_asset_horizon,
    get_all_finance_schools,
)
from src.services.logging import setup_logging, logger, log_aggregation


TRACKED_ASSETS = ["BTC", "GOLD", "SPX"]
HORIZONS = [Horizon.SHORT, Horizon.MEDIUM, Horizon.LONG]


async def aggregate_signals():
    """Main aggregation logic - compute and store current signals."""
    setup_logging()
    logger.info("Starting signal aggregation worker")
    
    async with AsyncSessionLocal() as session:
        # Get all finance schools
        finance_schools = await get_all_finance_schools(session)
        
        total_signals = 0
        
        # Aggregate for each asset and horizon
        for asset_symbol in TRACKED_ASSETS:
            for horizon in HORIZONS:
                try:
                    # Overall signal (all schools combined)
                    buy, neutral, sell, label = await aggregate_signals_for_asset_horizon(
                        session, asset_symbol, horizon, finance_school_id=None
                    )
                    
                    # Upsert overall signal
                    stmt = insert(CurrentSignal).values(
                        asset_symbol=asset_symbol,
                        horizon=horizon,
                        finance_school_id=None,
                        weighted_score_buy=buy,
                        weighted_score_neutral=neutral,
                        weighted_score_sell=sell,
                        final_label=label,
                        generated_at=datetime.utcnow(),
                    ).on_conflict_do_update(
                        index_elements=["asset_symbol", "horizon", "finance_school_id"],
                        set_={
                            "weighted_score_buy": buy,
                            "weighted_score_neutral": neutral,
                            "weighted_score_sell": sell,
                            "final_label": label,
                            "generated_at": datetime.utcnow(),
                        },
                    )
                    
                    await session.execute(stmt)
                    total_signals += 1
                    
                    log_aggregation(
                        asset_symbol,
                        horizon.value,
                        label.value,
                        buy,
                        neutral,
                        sell,
                    )
                    
                    # School-level signals
                    for school in finance_schools:
                        buy_s, neutral_s, sell_s, label_s = await aggregate_signals_for_asset_horizon(
                            session, asset_symbol, horizon, finance_school_id=school.id
                        )
                        
                        stmt = insert(CurrentSignal).values(
                            asset_symbol=asset_symbol,
                            horizon=horizon,
                            finance_school_id=school.id,
                            weighted_score_buy=buy_s,
                            weighted_score_neutral=neutral_s,
                            weighted_score_sell=sell_s,
                            final_label=label_s,
                            generated_at=datetime.utcnow(),
                        ).on_conflict_do_update(
                            index_elements=["asset_symbol", "horizon", "finance_school_id"],
                            set_={
                                "weighted_score_buy": buy_s,
                                "weighted_score_neutral": neutral_s,
                                "weighted_score_sell": sell_s,
                                "final_label": label_s,
                                "generated_at": datetime.utcnow(),
                            },
                        )
                        
                        await session.execute(stmt)
                        total_signals += 1
                        
                        log_aggregation(
                            asset_symbol,
                            horizon.value,
                            f"{label_s.value} ({school.name})",
                            buy_s,
                            neutral_s,
                            sell_s,
                        )
                    
                except Exception as e:
                    logger.error(
                        f"Error aggregating signals for {asset_symbol}/{horizon.value}: {e}"
                    )
                    continue
        
        await session.commit()
        logger.info(f"Signal aggregation complete - {total_signals} signals computed")


if __name__ == "__main__":
    asyncio.run(aggregate_signals())

