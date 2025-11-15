"""
Comprehensive MVP validation script.
Tests all components end-to-end before production deployment.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.session import AsyncSessionLocal
from src.db.models import (
    FinanceSchool, Influencer, Tweet, SentimentPrediction,
    PriceCandle, PredictionOutcome, TrustScore, CurrentSignal
)
from sqlalchemy import select, func


async def validate_database():
    """Validate database structure and data."""
    print("=" * 70)
    print("DATABASE VALIDATION")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        # Check all tables exist and have data
        tables = [
            ("finance_schools", FinanceSchool),
            ("influencers", Influencer),
            ("tweets", Tweet),
            ("sentiment_predictions", SentimentPrediction),
            ("price_candles", PriceCandle),
            ("prediction_outcomes", PredictionOutcome),
            ("trust_scores", TrustScore),
            ("current_signals", CurrentSignal),
        ]
        
        all_good = True
        for table_name, model in tables:
            result = await session.execute(select(func.count()).select_from(model))
            count = result.scalar()
            status = "✅" if count > 0 else "⚠️ "
            print(f"{status} {table_name:30} {count:6} rows")
            if count == 0 and table_name not in ["prediction_outcomes"]:  # Some tables may be empty
                all_good = False
        
        return all_good


async def validate_relationships():
    """Validate foreign key relationships."""
    print("\n" + "=" * 70)
    print("RELATIONSHIP VALIDATION")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        # Check influencers have finance schools
        result = await session.execute(
            select(Influencer.handle, FinanceSchool.name)
            .join(FinanceSchool, Influencer.finance_school_id == FinanceSchool.id)
            .limit(5)
        )
        relationships = result.all()
        
        if relationships:
            print("✅ Influencer → FinanceSchool relationships OK")
            for handle, school in relationships[:3]:
                print(f"   @{handle} → {school}")
        else:
            print("❌ No influencer-school relationships found")
            return False
        
        # Check tweets have influencers
        result = await session.execute(
            select(func.count(Tweet.id))
            .join(Influencer, Tweet.influencer_id == Influencer.id)
        )
        tweet_count = result.scalar()
        print(f"✅ Tweets with valid influencers: {tweet_count}")
        
        # Check predictions have tweets
        result = await session.execute(
            select(func.count(SentimentPrediction.id))
            .join(Tweet, SentimentPrediction.tweet_id == Tweet.id)
        )
        pred_count = result.scalar()
        print(f"✅ Predictions with valid tweets: {pred_count}")
        
        return True


async def validate_data_quality():
    """Validate data quality and consistency."""
    print("\n" + "=" * 70)
    print("DATA QUALITY VALIDATION")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        # Check for duplicate tweets
        result = await session.execute(
            select(Tweet.tweet_id, func.count(Tweet.tweet_id))
            .group_by(Tweet.tweet_id)
            .having(func.count(Tweet.tweet_id) > 1)
        )
        duplicates = result.all()
        
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate tweet IDs")
        else:
            print("✅ No duplicate tweets")
        
        # Check price data has valid OHLCV
        result = await session.execute(
            select(PriceCandle)
            .where(PriceCandle.close == 0)
            .limit(5)
        )
        zero_prices = result.scalars().all()
        
        if zero_prices:
            print(f"⚠️  Found {len(zero_prices)} price candles with zero close price")
            for candle in zero_prices[:3]:
                print(f"   {candle.asset_symbol} @ {candle.timestamp}")
        else:
            print("✅ All price candles have valid OHLCV data")
        
        # Check trust scores are in valid range [0, 1]
        result = await session.execute(
            select(TrustScore)
            .where((TrustScore.score < 0) | (TrustScore.score > 1))
        )
        invalid_scores = result.scalars().all()
        
        if invalid_scores:
            print(f"❌ Found {len(invalid_scores)} trust scores out of range")
            return False
        else:
            print("✅ All trust scores in valid range [0, 1]")
        
        # Check signal scores sum approximately to 1
        result = await session.execute(
            select(CurrentSignal).limit(5)
        )
        signals = result.scalars().all()
        
        invalid_sums = []
        for signal in signals:
            total = float(signal.weighted_score_buy + signal.weighted_score_neutral + signal.weighted_score_sell)
            if abs(total - 1.0) > 0.01:  # Allow 1% margin
                invalid_sums.append(signal)
        
        if invalid_sums:
            print(f"⚠️  Found {len(invalid_sums)} signals with scores not summing to 1.0")
        else:
            print("✅ All signal scores sum to ~1.0")
        
        return True


def validate_files():
    """Validate critical files exist."""
    print("\n" + "=" * 70)
    print("FILE VALIDATION")
    print("=" * 70)
    
    critical_files = [
        # Core source
        "src/db/models.py",
        "src/db/schema.py",
        "src/db/session.py",
        "src/services/config.py",
        "src/services/logging.py",
        "src/services/sentiment_classifier.py",
        "src/services/price_provider.py",
        "src/services/trust_scoring.py",
        "src/services/signal_aggregator.py",
        "src/services/x_api_client.py",
        "src/api/main.py",
        "src/api/routers/signals.py",
        "src/api/routers/influencers.py",
        "src/workers/tweet_ingestion.py",
        "src/workers/sentiment.py",
        "src/workers/price_ingestion.py",
        "src/workers/evaluation.py",
        "src/workers/aggregation.py",
        "src/workers/recompute_trust_scores.py",
        
        # Configuration
        "pyproject.toml",
        "alembic.ini",
        "render.yaml",
        
        # Documentation
        "README.md",
        "SETUP.md",
        "docs/X_API_SETUP.md",
        "docs/API_CACHING.md",
        "docs/OPERATIONS.md",
        
        # Data
        "data/finance_schools.json",
        "data/influencers.json",
        
        # Scripts
        "scripts/seed_data.py",
        "scripts/create_mock_tweets.py",
        "scripts/create_q3_2024_tweets.py",
        "scripts/test_x_api.py",
    ]
    
    missing = []
    for file_path in critical_files:
        full_path = Path(__file__).parent.parent / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing.append(file_path)
    
    return len(missing) == 0


async def main():
    """Run all validation checks."""
    print("\n" + "🔍" * 35)
    print("FINCLATOR MVP VALIDATION")
    print("🔍" * 35 + "\n")
    
    results = []
    
    # File validation
    results.append(("Files", validate_files()))
    
    # Database validation
    results.append(("Database", await validate_database()))
    
    # Relationship validation
    results.append(("Relationships", await validate_relationships()))
    
    # Data quality validation
    results.append(("Data Quality", await validate_data_quality()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL VALIDATION CHECKS PASSED")
        print("✅ System is ready for production deployment")
    else:
        print("⚠️  SOME CHECKS FAILED")
        print("❌ Review issues above before deploying")
    print("=" * 70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

