"""Test X API connection and fetch sample tweets."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.x_api_client import x_api_client
from src.services.config import settings
from src.services.logging import setup_logging, logger


async def test_x_api():
    """Test X API connection by fetching tweets for Sant Manukyan."""
    setup_logging()
    
    print("🐦 Testing X API Connection...\n")
    print("=" * 60)
    
    # Check if API key is configured
    if not settings.x_api_bearer_token:
        print("❌ X_API_BEARER_TOKEN not configured!")
        print("\nPlease set X_API_BEARER_TOKEN in your .env file:")
        print("  X_API_BEARER_TOKEN=your_bearer_token_here")
        print("\nGet an API key from https://developer.twitter.com/en/portal")
        return False
    
    print(f"✓ X_API_BEARER_TOKEN configured: {settings.x_api_bearer_token[:20]}...")
    print("")
    
    # Test username
    test_username = "SantManukyan"
    
    print(f"📡 Testing user lookup: @{test_username}")
    print("-" * 60)
    
    # Step 1: Get user ID
    user_id = await x_api_client.get_user_id_by_username(test_username)
    
    if not user_id:
        print(f"❌ Failed to fetch user ID for @{test_username}")
        print("\nPossible issues:")
        print("  1. Invalid X API Bearer Token")
        print("  2. Username doesn't exist")
        print("  3. Rate limit exceeded")
        print("  4. API permissions not configured")
        return False
    
    print(f"✓ User ID: {user_id}")
    print("")
    
    # Step 2: Fetch recent tweets
    print(f"📥 Fetching recent tweets for @{test_username}...")
    print("-" * 60)
    
    tweets = await x_api_client.get_user_tweets(
        username=test_username,
        max_results=10,  # Fetch 10 tweets
        since_hours=720  # Last 30 days (to maximize cache hits)
    )
    
    if not tweets:
        print(f"⚠️  No tweets found for @{test_username} in the last 7 days")
        print("\nThis might mean:")
        print("  1. User hasn't tweeted recently")
        print("  2. Rate limit exceeded")
        print("  3. API tier doesn't support tweet fetching")
        return False
    
    print(f"✓ Fetched {len(tweets)} tweets\n")
    
    # Display tweets
    print("📝 Sample Tweets:")
    print("=" * 60)
    
    for i, tweet in enumerate(tweets[:3], 1):  # Show first 3
        print(f"\n{i}. Tweet ID: {tweet['id']}")
        print(f"   Created: {tweet['created_at']}")
        print(f"   Text: {tweet['text'][:100]}...")
    
    print("\n" + "=" * 60)
    print("✅ X API integration working correctly!")
    print("")
    print("Next steps:")
    print("  1. Add more influencers to data/influencers.json")
    print("  2. Run tweet ingestion: python -m src.workers.tweet_ingestion")
    print("  3. Check cache: python scripts/cache_stats.py")
    
    return True


async def main():
    """Run the test."""
    try:
        success = await test_x_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

