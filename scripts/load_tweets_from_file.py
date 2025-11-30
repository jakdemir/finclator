"""Load tweets from JSON file into database for debugging."""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet
from src.workers.tweet_ingestion import detect_asset_symbols
from src.services.logging import setup_logging, logger


async def load_tweets_from_file(json_file: str, username: str = "SantManukyan"):
    """Load tweets from JSON file into database."""
    setup_logging()
    
    file_path = Path(json_file)
    if not file_path.exists():
        print(f"❌ File not found: {json_file}")
        return
    
    print(f"📂 Loading tweets from {json_file}...")
    
    # Load JSON
    with open(file_path, 'r') as f:
        tweets_data = json.load(f)
    
    if not isinstance(tweets_data, list):
        print("❌ JSON file must contain an array of tweets")
        return
    
    print(f"📊 Found {len(tweets_data)} tweets in file")
    
    # Get influencer
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Influencer).where(Influencer.handle == username)
        )
        influencer = result.scalar_one_or_none()
        
        if not influencer:
            print(f"❌ Influencer @{username} not found. Run seed_data.py first.")
            return
        
        print(f"✓ Found influencer: @{influencer.handle}")
        print()
        
        stored = 0
        skipped = 0
        
        for tweet_data in tweets_data:
            # Handle different JSON formats
            if isinstance(tweet_data, dict):
                tweet_id = str(tweet_data.get('id', ''))
                tweet_text = tweet_data.get('text', '')
                
                # Parse created_at
                created_at_str = tweet_data.get('created_at', '')
                if isinstance(created_at_str, str):
                    try:
                        # Try ISO format
                        if 'T' in created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            created_at = datetime.fromisoformat(created_at_str)
                    except:
                        created_at = datetime.utcnow()
                else:
                    created_at = datetime.utcnow()
            else:
                continue
            
            # Detect assets
            asset_symbols = detect_asset_symbols(tweet_text)
            if not asset_symbols:
                skipped += 1
                continue
            
            # Insert tweet
            stmt = insert(Tweet).values(
                influencer_id=influencer.id,
                tweet_id=tweet_id,
                text=tweet_text,
                tweeted_at=created_at,
                asset_symbols=asset_symbols,
                ingested_at=datetime.utcnow(),
                processed_for_sentiment=False,
            ).on_conflict_do_nothing(index_elements=["tweet_id"])
            
            result = await session.execute(stmt)
            if result.rowcount > 0:
                stored += 1
                logger.info(f"✓ Stored tweet {tweet_id[:10]}... (assets: {', '.join(asset_symbols)})")
        
        await session.commit()
        
        print()
        print("=" * 70)
        print(f"✅ Loaded {stored} tweets into database")
        print(f"⊘ Skipped {skipped} tweets (no assets detected)")
        print()
        print("Next steps:")
        print("  1. Run: python scripts/mvp_sant_manukyan.py")
        print("     (or just: python -m src.workers.sentiment)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_tweets_from_file.py <json_file> [username]")
        print()
        print("Example:")
        print("  python scripts/load_tweets_from_file.py data/sant_tweets.json SantManukyan")
        sys.exit(1)
    
    json_file = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "SantManukyan"
    
    asyncio.run(load_tweets_from_file(json_file, username))

