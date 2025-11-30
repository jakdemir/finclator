"""Efficiently fetch last 100 tweets for a user."""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.x_api_client import x_api_client
from src.services.logging import setup_logging, logger


async def get_last_100_tweets(username: str, wait_on_rate_limit: bool = False):
    """
    Get last 100 tweets efficiently - single API call.
    
    Uses only 1 API request (out of 50 allowed per 15 minutes).
    Leverages built-in caching (90-day TTL) if available.
    
    Args:
        username: X username (without @)
        wait_on_rate_limit: If True, wait 16 minutes and retry on rate limit
    """
    setup_logging()
    
    print(f"📥 Fetching last 100 tweets for @{username}...")
    print("=" * 60)
    
    # Single API call - max 100 tweets
    # No date filtering = most recent tweets
    try:
        tweets = await x_api_client.get_user_tweets(
            username=username,
            max_results=100,  # X API max per request
            since_hours=720  # Last 30 days (to ensure we get recent tweets)
        )
    except Exception as e:
        if "429" in str(e) or "Too Many Requests" in str(e):
            print(f"\n⚠️  Rate limit hit (429 Too Many Requests)")
            print(f"   X API free tier: 50 requests per 15 minutes")
            print(f"   Current limit: Rate limit active")
            
            if wait_on_rate_limit:
                print(f"\n⏳ Waiting 16 minutes for rate limit to reset...")
                import asyncio
                await asyncio.sleep(960)  # 16 minutes
                print(f"   ↻ Retrying...")
                tweets = await x_api_client.get_user_tweets(
                    username=username,
                    max_results=100,
                    since_hours=720
                )
            else:
                print(f"\n💡 Options:")
                print(f"   1. Wait 15-20 minutes and run again")
                print(f"   2. Run with --wait flag: python scripts/get_recent_tweets.py {username} --wait")
                return []
        else:
            raise
    
    print(f"\n✅ Fetched {len(tweets)} tweets")
    print(f"📊 API requests used: 1 (out of 50 allowed per 15 min)")
    
    if tweets:
        print(f"\n📅 Date range:")
        print(f"   Oldest: {tweets[-1]['created_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Newest: {tweets[0]['created_at'].strftime('%Y-%m-%d %H:%M')}")
        
        # Show sample tweets
        print(f"\n📝 Sample tweets (first 3):")
        for i, tweet in enumerate(tweets[:3], 1):
            print(f"\n{i}. {tweet['created_at'].strftime('%Y-%m-%d %H:%M')}")
            print(f"   {tweet['text'][:100]}...")
    
    return tweets


async def main():
    """Main function."""
    username = sys.argv[1] if len(sys.argv) > 1 else "SantManukyan"
    wait_on_rate_limit = "--wait" in sys.argv or "-w" in sys.argv
    
    tweets = await get_last_100_tweets(username, wait_on_rate_limit=wait_on_rate_limit)
    
    # Optionally save to file
    if tweets:
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        if not output_file:
            # Default output file
            output_file = f"data/{username}_recent_tweets_{Path(__file__).parent.parent.name}.json"
            # Actually, let's use a timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"data/{username}_tweets_{timestamp}.json"
        
        output_path = Path(__file__).parent.parent / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert datetime objects to strings for JSON
        exportable_tweets = []
        for tweet in tweets:
            exportable_tweets.append({
                'id': tweet['id'],
                'text': tweet['text'],
                'created_at': tweet['created_at'].isoformat(),
                'author_username': tweet.get('author_username', username)
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exportable_tweets, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved {len(tweets)} tweets to {output_path}")
        print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    asyncio.run(main())

