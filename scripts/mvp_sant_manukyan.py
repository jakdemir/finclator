"""MVP: Process Sant Manukyan's tweets, compare with market data, assign trust score."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet, SentimentPrediction, PriceCandle, PredictionOutcome, TrustScore
from src.services.x_api_client import x_api_client
from src.services.logging import setup_logging, logger
from src.workers.tweet_ingestion import detect_asset_symbols
from src.workers.sentiment import process_tweets
from src.workers.price_ingestion import ingest_prices
from src.workers.evaluation import evaluate_predictions
from src.services.trust_scoring import compute_trust_scores_for_influencer


async def ensure_sant_manukyan():
    """Ensure Sant Manukyan exists in database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Influencer).where(Influencer.handle == "SantManukyan")
        )
        influencer = result.scalar_one_or_none()
        
        if not influencer:
            from src.db.models import FinanceSchool
            # Get or create finance school
            school_result = await session.execute(
                select(FinanceSchool).where(FinanceSchool.name == "Hand-Picked / Macro")
            )
            school = school_result.scalar_one_or_none()
            
            if not school:
                school = FinanceSchool(
                    name="Hand-Picked / Macro",
                    description="Hand-selected macroeconomic strategists"
                )
                session.add(school)
                await session.flush()
            
            influencer = Influencer(
                handle="SantManukyan",
                display_name="Sant Manukyan",
                finance_school_id=school.id
            )
            session.add(influencer)
            await session.commit()
            await session.refresh(influencer)
            logger.info(f"✓ Created influencer: {influencer.handle}")
        
        return influencer


async def fetch_tweets(influencer):
    """Fetch recent tweets for Sant Manukyan."""
    logger.info("Step 1: Fetching tweets...")
    
    try:
        tweets = await x_api_client.get_user_tweets(
            username="SantManukyan",
            max_results=100,
            since_hours=720  # Last 30 days
        )
    except Exception as e:
        if "429" in str(e) or "Too Many Requests" in str(e):
            logger.error("Rate limit hit - cannot fetch new tweets")
            logger.info("💡 Options:")
            logger.info("  1. Wait 15-20 minutes and run again")
            logger.info("  2. Use cached data if available")
            logger.info("  3. Load tweets from JSON file: python scripts/load_tweets_from_file.py <file>")
            return 0
        else:
            raise
    
    if not tweets:
        logger.warning("No tweets fetched")
        return 0
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy.dialects.postgresql import insert
        from datetime import datetime
        
        stored = 0
        for tweet in tweets:
            asset_symbols = detect_asset_symbols(tweet['text'])
            if not asset_symbols:
                continue
            
            stmt = insert(Tweet).values(
                influencer_id=influencer.id,
                tweet_id=str(tweet['id']),
                text=tweet['text'],
                tweeted_at=tweet['created_at'],
                asset_symbols=asset_symbols,
                ingested_at=datetime.utcnow(),
                processed_for_sentiment=False,
            ).on_conflict_do_nothing(index_elements=["tweet_id"])
            
            result = await session.execute(stmt)
            if result.rowcount > 0:
                stored += 1
        
        await session.commit()
        logger.info(f"✓ Stored {stored} new tweets")
        return stored


async def process_sentiments(influencer):
    """Classify sentiment for unprocessed tweets."""
    logger.info("Step 2: Classifying sentiment...")
    await process_tweets()


async def fetch_prices():
    """Fetch price data for all assets."""
    logger.info("Step 3: Fetching price data...")
    await ingest_prices()


async def evaluate(influencer):
    """Evaluate predictions against market data."""
    logger.info("Step 4: Evaluating predictions...")
    await evaluate_predictions()


async def calculate_trust_score(influencer):
    """Calculate trust score for Sant Manukyan."""
    logger.info("Step 5: Calculating trust score...")
    
    async with AsyncSessionLocal() as session:
        scores = await compute_trust_scores_for_influencer(
            session,
            influencer.id,
            window_days=None  # All historical data (per clarification Q2)
        )
        
        for score in scores:
            session.add(score)
        
        await session.commit()
        
        logger.info(f"✓ Calculated {len(scores)} trust scores")
        for score in scores:
            asset_str = score.asset_symbol if score.asset_symbol else "OVERALL"
            logger.info(f"  {asset_str}/{score.horizon.value}: {score.score:.4f}")


async def main():
    """Run MVP pipeline for Sant Manukyan."""
    setup_logging()
    
    print("=" * 70)
    print("MVP: Sant Manukyan Trust Score Analysis")
    print("=" * 70)
    print()
    
    # Step 0: Ensure influencer exists
    influencer = await ensure_sant_manukyan()
    print(f"Influencer: @{influencer.handle} (ID: {influencer.id})")
    print()
    
    # Step 1: Fetch tweets
    await fetch_tweets(influencer)
    print()
    
    # Step 2: Classify sentiment
    await process_sentiments(influencer)
    print()
    
    # Step 3: Fetch price data
    await fetch_prices()
    print()
    
    # Step 4: Evaluate predictions
    await evaluate(influencer)
    print()
    
    # Step 5: Calculate trust score
    await calculate_trust_score(influencer)
    print()
    
    print("=" * 70)
    print("✅ MVP Pipeline Complete")
    print("=" * 70)
    print()
    print("View trust score via API:")
    print(f"  curl http://localhost:8000/influencers/{influencer.id}")


if __name__ == "__main__":
    asyncio.run(main())

