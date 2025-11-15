"""Create Q3 2024 mock tweets for Sant Manukyan to test historical evaluation."""
import asyncio
from datetime import datetime
import uuid
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.session import AsyncSessionLocal
from src.db.models import Tweet, Influencer
from sqlalchemy import select

async def create_q3_2024_mock_tweets():
    print("📝 Creating Q3 2024 Mock Tweets for Historical Testing\n")
    print("=" * 70)
    print("Influencer: Sant Manukyan")
    print("Period: Q3 2024 (July-September)")
    print("Purpose: Test prediction evaluation against real market data")
    print("=" * 70)

    # Q3 2024 mock tweets with realistic market commentary
    q3_2024_tweets = [
        # July 2024 - Early Q3
        {
            "text": "Bitcoin consolidating around $60k. Short-term outlook neutral but medium-term bullish on fundamentals. Watching macro closely. #BTC",
            "date": "2024-07-05",
            "assets": ["BTC"],
        },
        {
            "text": "Gold breaking all-time highs again. Central bank buying continues. Long-term structural bull market intact. #GOLD",
            "date": "2024-07-12",
            "assets": ["GOLD"],
        },
        {
            "text": "S&P 500 at new highs. Tech earnings strong. Market breadth improving. Bullish for Q3. $SPY",
            "date": "2024-07-18",
            "assets": ["SPX"],
        },
        
        # August 2024 - Mid Q3
        {
            "text": "BTC showing strength above $65k. ETF flows positive. Next target $70k+ in coming months. #Bitcoin",
            "date": "2024-08-02",
            "assets": ["BTC"],
        },
        {
            "text": "Macro environment shifting. Fed signals potential rate cuts. Bullish for gold and risk assets medium-term.",
            "date": "2024-08-08",
            "assets": ["GOLD", "SPX"],
        },
        {
            "text": "Markets volatile this week but fundamentals remain strong. Buying the dip on quality names. S&P 500 dip looks like opportunity.",
            "date": "2024-08-15",
            "assets": ["SPX"],
        },
        {
            "text": "Bitcoin breaking out! $70k next week is very possible. Momentum building. This rally has legs. #BTC",
            "date": "2024-08-22",
            "assets": ["BTC"],
        },
        
        # September 2024 - Late Q3
        {
            "text": "Fed cuts incoming. Gold about to explode higher. $2600+ target for year-end. Historic bull market. #GOLD",
            "date": "2024-09-05",
            "assets": ["GOLD"],
        },
        {
            "text": "Risk-on across all assets. Bitcoin, gold, stocks all rallying. Fed pivot bullish for everything. Enjoy the ride.",
            "date": "2024-09-12",
            "assets": ["BTC", "GOLD", "SPX"],
        },
        {
            "text": "Q4 setup looking excellent. Bitcoin consolidating for next leg up. Target $80k by year-end. #BTC",
            "date": "2024-09-25",
            "assets": ["BTC"],
        },
    ]

    async with AsyncSessionLocal() as session:
        # Get Sant Manukyan from database
        result = await session.execute(
            select(Influencer).where(Influencer.handle == "SantManukyan")
        )
        influencer = result.scalar_one_or_none()

        if not influencer:
            print("\n❌ Sant Manukyan not found in database!")
            print("\nPlease run: python scripts/seed_data.py")
            return

        print(f"\n✓ Found influencer: {influencer.display_name}\n")
        print("Creating tweets:\n")

        created_count = 0
        for tweet_data in q3_2024_tweets:
            tweet_id = str(uuid.uuid4())
            tweeted_at = datetime.strptime(tweet_data["date"], "%Y-%m-%d")

            tweet = Tweet(
                influencer_id=influencer.id,
                tweet_id=tweet_id,
                text=tweet_data["text"],
                tweeted_at=tweeted_at,
                asset_symbols=tweet_data["assets"],
                ingested_at=datetime.utcnow(),
                processed_for_sentiment=False
            )
            session.add(tweet)
            created_count += 1
            
            print(f"✓ {tweet_data['date']} - {tweet_data['text'][:60]}...")
            print(f"  Assets: {', '.join(tweet_data['assets'])}\n")

        await session.commit()
        
        print("=" * 70)
        print(f"✅ Created {created_count} Q3 2024 mock tweets!\n")
        
        print("=" * 70)
        print("Next Steps - Full Historical Pipeline Test:")
        print("=" * 70)
        print("\n1. Classify sentiment:")
        print("   python -m src.workers.sentiment")
        print("\n2. Fetch historical price data:")
        print("   python -m src.workers.price_ingestion")
        print("   (Already have 2024 data)")
        print("\n3. Evaluate predictions (Q3 tweets vs Q3-Q4 prices):")
        print("   python -m src.workers.evaluation")
        print("   This will compare SHORT/MEDIUM/LONG predictions against actual outcomes!")
        print("\n4. Calculate trust scores:")
        print("   python scripts/calculate_trust_scores.py")
        print("\n5. Aggregate signals:")
        print("   python -m src.workers.aggregation")
        print("\n6. Query results:")
        print("   curl 'http://localhost:8000/signals?asset=BTC&horizon=SHORT'")
        print("\n" + "=" * 70)
        print("\n💡 This tests the CORE value prop:")
        print("   Historical predictions → Actual outcomes → Trust scores → Signals")
        print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(create_q3_2024_mock_tweets())

