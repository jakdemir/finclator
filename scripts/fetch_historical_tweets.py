"""Fetch historical tweets from Q3 2024 for testing pipeline with real data."""
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet
from src.services.x_api_client import x_api_client
from src.services.logging import setup_logging, logger
from src.workers.tweet_ingestion import detect_asset_symbols


async def fetch_q3_2024_tweets():
    """Fetch Sant Manukyan's tweets from Q3 2024 (July-September)."""
    setup_logging()
    
    print("📅 Fetching Q3 2024 Historical Tweets")
    print("=" * 70)
    print("\nTarget Period: July 1 - September 30, 2024")
    print("Influencer: Sant Manukyan (@SantManukyan)")
    print("Tweets to fetch: 10\n")
    
    # Q3 2024 date range
    start_time = datetime(2024, 7, 1, 0, 0, 0)
    end_time = datetime(2024, 9, 30, 23, 59, 59)
    
    # Convert to ISO 8601 format for X API
    start_time_iso = start_time.isoformat() + "Z"
    end_time_iso = end_time.isoformat() + "Z"
    
    days_span = (end_time - start_time).days
    
    print(f"Time span: {days_span} days")
    print("-" * 70)
    
    # Fetch tweets from X API
    print("\n📡 Fetching tweets from X API...")
    
    try:
        tweets = await x_api_client.get_user_tweets(
            username="SantManukyan",
            max_results=10,
            start_time=start_time_iso,
            end_time=end_time_iso
        )
        
        if not tweets:
            print("❌ No tweets found for Q3 2024")
            print("\nPossible reasons:")
            print("  1. Sant Manukyan didn't tweet during Q3 2024")
            print("  2. Rate limit exceeded (wait 15 minutes)")
            print("  3. API tier doesn't support historical data")
            return
        
        print(f"✓ Fetched {len(tweets)} tweets\n")
        
        # Display tweet preview
        print("📝 Tweet Preview:")
        print("=" * 70)
        for i, tweet in enumerate(tweets[:5], 1):  # Show first 5
            print(f"\n{i}. {tweet['created_at'].strftime('%Y-%m-%d %H:%M')}")
            print(f"   ID: {tweet['id']}")
            print(f"   Text: {tweet['text'][:100]}...")
            
            # Detect assets
            assets = detect_asset_symbols(tweet['text'])
            if assets:
                print(f"   Assets: {', '.join(assets)}")
        
        if len(tweets) > 5:
            print(f"\n... and {len(tweets) - 5} more tweets")
        
        print("\n" + "=" * 70)
        
        # Store tweets in database
        print("\n💾 Storing tweets in database...")
        
        async with AsyncSessionLocal() as session:
            # Get Sant Manukyan's influencer record
            result = await session.execute(
                select(Influencer).where(Influencer.handle == "SantManukyan")
            )
            influencer = result.scalar_one_or_none()
            
            if not influencer:
                print("❌ Sant Manukyan not found in database!")
                print("\nRun: python scripts/seed_data.py")
                return
            
            stored_count = 0
            for tweet in tweets:
                # Detect assets
                asset_symbols = detect_asset_symbols(tweet['text'])
                
                if not asset_symbols:
                    print(f"  ⊘ Skipping tweet {tweet['id'][:10]}... (no assets detected)")
                    continue
                
                # Insert tweet (on conflict do nothing)
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
                    stored_count += 1
                    print(f"  ✓ Stored tweet {tweet['id'][:10]}... (assets: {', '.join(asset_symbols)})")
            
            await session.commit()
            
            print(f"\n✅ Stored {stored_count} new tweets in database")
            
            if stored_count == 0:
                print("\nℹ️  All tweets were already in the database (or had no assets)")
        
        print("\n" + "=" * 70)
        print("Next Steps:")
        print("=" * 70)
        print("\n1. Run sentiment classification:")
        print("   python -m src.workers.sentiment")
        print("\n2. Fetch historical price data for Q3 2024:")
        print("   python -m src.workers.price_ingestion")
        print("\n3. Evaluate predictions (compare sentiment vs actual prices):")
        print("   python -m src.workers.evaluation")
        print("\n4. Aggregate signals:")
        print("   python -m src.workers.aggregation")
        print("\n5. Query results:")
        print("   curl 'http://localhost:8000/signals?asset=BTC&horizon=SHORT'")
        print("\nOr run all at once:")
        print("   ./scripts/run_pipeline.sh")
        print("\n" + "=" * 70)
        
    except Exception as e:
        logger.error(f"Error fetching historical tweets: {e}")
        print(f"\n❌ Error: {e}")
        
        if "429" in str(e):
            print("\n⏳ Rate limit hit. Please wait 15 minutes and try again.")
        else:
            print("\nCheck logs for details.")


if __name__ == "__main__":
    asyncio.run(fetch_q3_2024_tweets())

