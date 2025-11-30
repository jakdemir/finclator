"""Load tweets from CSV file into database."""
import asyncio
import csv
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


async def load_tweets_from_csv(csv_file: str, username: str = "SantManukyan"):
    """Load tweets from CSV file into database."""
    setup_logging()
    
    file_path = Path(csv_file)
    if not file_path.exists():
        print(f"❌ File not found: {csv_file}")
        return
    
    print(f"📂 Loading tweets from {csv_file}...")
    
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
        errors = 0
        
        # Read CSV file (handle BOM - Byte Order Mark)
        with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            
            row_num = 0
            for row in reader:
                row_num += 1
                try:
                    # Handle BOM in column names (first column might have \ufeff prefix)
                    tweet_id_key = 'tweet_id'
                    if tweet_id_key not in row and '\ufefftweet_id' in row:
                        tweet_id_key = '\ufefftweet_id'
                    
                    tweet_id = row.get(tweet_id_key, '').strip("'\"")
                    tweet_text = row.get('text', '').strip()
                    tweet_type = row.get('type', '').strip()
                    created_at_str = row.get('created_at', '').strip()
                    
                    # Skip if missing required fields
                    if not tweet_id or not tweet_text:
                        skipped += 1
                        continue
                    
                    # Skip replies (optional - you can change this)
                    # Commented out to load all tweets including replies
                    # if tweet_type == 'Reply':
                    #     skipped += 1
                    #     continue
                    
                    # Parse created_at
                    try:
                        # Format: 2025-11-28 08:55:30
                        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            # Try ISO format
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        except:
                            created_at = datetime.utcnow()
                    
                    # Detect assets (store all tweets even if no assets detected)
                    asset_symbols = detect_asset_symbols(tweet_text)
                    if not asset_symbols:
                        asset_symbols = []  # Empty list if no assets detected
                        logger.debug(f"No assets detected for tweet {tweet_id[:10]}... - storing anyway. Text preview: {tweet_text[:50]}")
                    
                    # Insert tweet
                    try:
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
                            assets_str = ', '.join(asset_symbols) if asset_symbols else 'none'
                            logger.info(f"✓ Stored tweet {tweet_id[:10]}... (assets: {assets_str})")
                        else:
                            logger.debug(f"Tweet {tweet_id[:10]}... already exists (skipped)")
                    except Exception as e:
                        logger.error(f"✗ Error inserting tweet {tweet_id[:10]}...: {e}")
                        errors += 1
                        continue
                
                except Exception as e:
                    errors += 1
                    logger.error(f"✗ Error processing tweet: {e}")
                    continue
        
        await session.commit()
        
        print()
        print("=" * 70)
        print(f"✅ Loaded {stored} tweets into database")
        print(f"⊘ Skipped {skipped} tweets (missing required fields)")
        if errors > 0:
            print(f"⚠️  {errors} errors encountered")
        print()
        print("Next steps:")
        print("  1. Run: python -m src.workers.sentiment")
        print("  2. Run: python -m src.workers.price_ingestion")
        print("  3. Run: python -m src.workers.evaluation")
        print("  4. Run: python -m src.workers.signal_aggregation")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_tweets_from_csv.py <csv_file> [username]")
        print()
        print("Example:")
        print("  python scripts/load_tweets_from_csv.py data/TwExportly_santmanukyan_tweets_2025_11_30.csv SantManukyan")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "SantManukyan"
    
    asyncio.run(load_tweets_from_csv(csv_file, username))

