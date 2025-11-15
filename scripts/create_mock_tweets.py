"""Create mock tweets for testing the Finclator pipeline."""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet
from sqlalchemy import select


# Realistic mock tweets with clear sentiment signals
MOCK_TWEETS = [
    # Bullish BTC - Short term
    {
        "text": "Bitcoin breaking out above $90k! Strong momentum. Loading up more BTC this week. #Bitcoin #Crypto",
        "assets": ["BTC"],
        "days_ago": 1,
    },
    {
        "text": "BTC chart looking extremely bullish. Expecting new ATH within the next month. Time to accumulate! 🚀",
        "assets": ["BTC"],
        "days_ago": 2,
    },
    {
        "text": "Bitcoin showing incredible strength today. This rally has legs. Buy the dip!",
        "assets": ["BTC"],
        "days_ago": 3,
    },
    
    # Bearish BTC - Short term
    {
        "text": "Bitcoin looks overextended here. Expecting a pullback this week. Taking profits. #BTC",
        "assets": ["BTC"],
        "days_ago": 1,
    },
    {
        "text": "BTC needs to cool off. Resistance at $92k is strong. Shorting here for a quick trade.",
        "assets": ["BTC"],
        "days_ago": 2,
    },
    
    # Bullish GOLD - Medium term
    {
        "text": "Gold breaking all-time highs. Central banks buying aggressively. Bullish for next 6 months minimum. #Gold",
        "assets": ["GOLD"],
        "days_ago": 5,
    },
    {
        "text": "With inflation concerns rising, gold is the place to be. Expecting $2,500+ within the year.",
        "assets": ["GOLD"],
        "days_ago": 7,
    },
    {
        "text": "GLD showing strong accumulation. This gold rally is just getting started. Long term bullish.",
        "assets": ["GOLD"],
        "days_ago": 10,
    },
    
    # Bearish SPX - Short term
    {
        "text": "S&P 500 looking toppy here. Risk/reward not favorable. Reducing exposure this week. #SPX #StockMarket",
        "assets": ["SPX"],
        "days_ago": 1,
    },
    {
        "text": "SPY breaking down from key support. Expecting further weakness in the near term. Defensive positioning.",
        "assets": ["SPX"],
        "days_ago": 2,
    },
    
    # Bullish SPX - Long term
    {
        "text": "Despite short-term volatility, S&P 500 fundamentals remain strong. 5+ year outlook is bullish. Hold quality stocks.",
        "assets": ["SPX"],
        "days_ago": 30,
    },
    {
        "text": "Long-term investors should stay invested in the S&P. Tech innovation will drive next decade of growth.",
        "assets": ["SPX"],
        "days_ago": 45,
    },
    
    # Neutral / Mixed
    {
        "text": "Markets are sideways. No clear direction in BTC right now. Waiting for a better setup.",
        "assets": ["BTC"],
        "days_ago": 4,
    },
    {
        "text": "Bitcoin consolidating here. Could go either way. Not taking a position yet.",
        "assets": ["BTC"],
        "days_ago": 5,
    },
    
    # Multi-asset tweets
    {
        "text": "Risk-on environment: stocks up, gold up, crypto pumping. Everything rallying today! #Bitcoin #Gold #Stocks",
        "assets": ["BTC", "GOLD", "SPX"],
        "days_ago": 3,
    },
    {
        "text": "Safe haven flows: Gold and Bitcoin both benefiting from macro uncertainty. Bullish on both.",
        "assets": ["BTC", "GOLD"],
        "days_ago": 7,
    },
    
    # More varied signals
    {
        "text": "BTC at crucial support level. If it holds, we rally hard. If it breaks, look out below. Watching closely.",
        "assets": ["BTC"],
        "days_ago": 6,
    },
    {
        "text": "Gold miners showing strength. GDX breaking out. This confirms the gold bull market thesis.",
        "assets": ["GOLD"],
        "days_ago": 12,
    },
    {
        "text": "S&P earnings season starting strong. Market optimism building. Expecting continuation higher.",
        "assets": ["SPX"],
        "days_ago": 15,
    },
    {
        "text": "Bitcoin dominance rising. Alt season over. BTC is where the smart money is going.",
        "assets": ["BTC"],
        "days_ago": 8,
    },
]


async def create_mock_tweets():
    """Insert mock tweets for all influencers."""
    print("📝 Creating mock tweets for testing...\n")
    
    async with AsyncSessionLocal() as session:
        # Get all influencers
        result = await session.execute(select(Influencer))
        influencers = result.scalars().all()
        
        if not influencers:
            print("❌ No influencers found. Run seed_data.py first!")
            return
        
        print(f"Found {len(influencers)} influencers:")
        for inf in influencers:
            print(f"  - @{inf.handle} ({inf.display_name})")
        print()
        
        tweets_created = 0
        
        # Distribute tweets across influencers
        for i, tweet_data in enumerate(MOCK_TWEETS):
            # Assign to influencer (round-robin)
            influencer = influencers[i % len(influencers)]
            
            # Calculate tweet timestamp
            tweeted_at = datetime.utcnow() - timedelta(days=tweet_data["days_ago"])
            
            # Create unique tweet_id (mock)
            tweet_id = f"mock_{influencer.handle}_{int(tweeted_at.timestamp())}"
            
            # Check if tweet already exists
            existing = await session.execute(
                select(Tweet).where(Tweet.tweet_id == tweet_id)
            )
            if existing.scalar_one_or_none():
                continue
            
            # Create tweet
            tweet = Tweet(
                influencer_id=influencer.id,
                tweet_id=tweet_id,
                text=tweet_data["text"],
                tweeted_at=tweeted_at,
                asset_symbols=tweet_data["assets"],
                processed_for_sentiment=False,  # Will be processed by sentiment worker
            )
            
            session.add(tweet)
            tweets_created += 1
            
            print(f"✓ Created tweet for @{influencer.handle}")
            print(f"  Text: {tweet_data['text'][:80]}...")
            print(f"  Assets: {', '.join(tweet_data['assets'])}")
            print(f"  Date: {tweeted_at.strftime('%Y-%m-%d')}")
            print()
        
        await session.commit()
        
        print(f"\n✅ Created {tweets_created} mock tweets!")
        print("\nNext steps:")
        print("1. Run sentiment classification: python -m src.workers.sentiment")
        print("2. Run aggregation: python -m src.workers.aggregation")
        print("3. Query signals: curl 'http://localhost:8000/signals?asset=BTC&horizon=SHORT'")
        print("\nOr run the full pipeline: ./scripts/run_pipeline.sh")


if __name__ == "__main__":
    asyncio.run(create_mock_tweets())

