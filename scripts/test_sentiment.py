"""Test script for Hugging Face sentiment classification."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.sentiment_classifier import SentimentClassifier


async def test_sentiment():
    """Test sentiment classification with sample tweets."""
    
    print("🧪 Testing Hugging Face Sentiment Classification\n")
    print("=" * 60)
    
    classifier = SentimentClassifier()
    
    # Sample tweets for testing
    test_tweets = [
        {
            "text": "Bitcoin is breaking out! ATH incoming, load up now!",
            "asset": "BTC",
            "expected": "BUY"
        },
        {
            "text": "Gold hitting new all-time highs. Bullish for the next 5 years.",
            "asset": "GOLD",
            "expected": "BUY"
        },
        {
            "text": "S&P 500 looking weak, expecting a dump this week.",
            "asset": "SPX",
            "expected": "SELL"
        },
        {
            "text": "Just had coffee. Nice day today!",
            "asset": "BTC",
            "expected": "N/A (not market-related)"
        },
        {
            "text": "Market is sideways, no clear direction yet.",
            "asset": "BTC",
            "expected": "NEUTRAL"
        }
    ]
    
    for i, tweet in enumerate(test_tweets, 1):
        print(f"\n📝 Test {i}/{len(test_tweets)}")
        print(f"Tweet: \"{tweet['text']}\"")
        print(f"Asset: {tweet['asset']}")
        print(f"Expected: {tweet['expected']}")
        
        # Test noise filter
        is_relevant = await classifier.is_market_relevant(tweet['text'])
        print(f"Market Relevant: {'✓ Yes' if is_relevant else '✗ No'}")
        
        if is_relevant:
            # Test sentiment classification
            result = await classifier.classify_sentiment(tweet['text'], tweet['asset'])
            
            if result:
                print(f"✅ Direction: {result['direction']}")
                print(f"   Horizon: {result['horizon']}")
                print(f"   Confidence: {result['confidence']:.2%}")
            else:
                print("⚠ Classification failed")
        
        print("-" * 60)
    
    print("\n✅ Testing complete!")
    print("\nNext steps:")
    print("1. Get your free Hugging Face API key: https://huggingface.co/settings/tokens")
    print("2. Add to .env: HUGGINGFACE_API_KEY=hf_your_token_here")
    print("3. Run: ./scripts/run_pipeline.sh")


if __name__ == "__main__":
    asyncio.run(test_sentiment())

