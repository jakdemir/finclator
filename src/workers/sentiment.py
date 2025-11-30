"""Sentiment analysis worker - classifies unprocessed tweets."""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, update

from src.db.session import AsyncSessionLocal
from src.db.models import Tweet, SentimentPrediction, Influencer, Direction, Horizon
from src.services.sentiment_classifier import sentiment_classifier
from src.services.config import settings
from src.services.logging import setup_logging, logger, log_classification


def calculate_maturity_date(horizon: str, tweeted_at: datetime) -> datetime:
    """
    Calculate when a prediction matures for evaluation.
    
    Args:
        horizon: SHORT, MEDIUM, or LONG
        tweeted_at: Tweet timestamp
        
    Returns:
        Maturity datetime
    """
    if horizon == "SHORT":
        return tweeted_at + timedelta(days=90)  # 3 months
    elif horizon == "MEDIUM":
        return tweeted_at + timedelta(days=365)  # 12 months
    else:  # LONG
        return tweeted_at + timedelta(days=365 * 2)  # 2 years (conservative for 1-5+ years)


async def process_tweets():
    """Main sentiment processing logic."""
    setup_logging()
    logger.info("Starting sentiment analysis worker")
    
    async with AsyncSessionLocal() as session:
        # Get unprocessed tweets
        result = await session.execute(
            select(Tweet, Influencer)
            .join(Influencer, Tweet.influencer_id == Influencer.id)
            .where(Tweet.processed_for_sentiment == False)
            .limit(100)  # Process in batches
        )
        tweets_with_influencers = result.all()
        
        if not tweets_with_influencers:
            logger.info("No unprocessed tweets found")
            return
        
        logger.info(f"Processing {len(tweets_with_influencers)} tweets")
        
        processed_count = 0
        for tweet, influencer in tweets_with_influencers:
            try:
                # First, filter noise
                is_relevant = await sentiment_classifier.is_market_relevant(tweet.text)
                
                if not is_relevant:
                    logger.info(f"Tweet {tweet.tweet_id} filtered as noise")
                    # Mark as processed even if filtered
                    await session.execute(
                        update(Tweet)
                        .where(Tweet.id == tweet.id)
                        .values(processed_for_sentiment=True)
                    )
                    continue
                
                # Classify sentiment for each detected asset
                for asset_symbol in tweet.asset_symbols:
                    classification = await sentiment_classifier.classify_sentiment(
                        tweet.text, asset_symbol
                    )
                    
                    if classification:
                        # Create sentiment prediction
                        # Use model name - agent or HuggingFace model
                        if settings.use_agent_sentiment:
                            model_version = "openai-agent"
                        else:
                            model_version = settings.sentiment_model.split('/')[-1]  # Extract model name
                        prediction = SentimentPrediction(
                            tweet_id=tweet.id,
                            asset_symbol=asset_symbol,
                            direction=Direction[classification["direction"]],
                            horizon=Horizon[classification["horizon"]],
                            model_version=model_version,
                            confidence=float(classification["confidence"]),
                            created_at=datetime.utcnow(),
                            matures_at=calculate_maturity_date(
                                classification["horizon"], tweet.tweeted_at
                            ),
                            evaluated=False,
                        )
                        
                        session.add(prediction)
                        
                        log_classification(
                            str(tweet.id),
                            asset_symbol,
                            classification["direction"],
                            classification["horizon"],
                            classification["confidence"],
                        )
                    else:
                        logger.warning(f"Failed to classify tweet {tweet.tweet_id} for {asset_symbol}")
                
                # Mark tweet as processed
                await session.execute(
                    update(Tweet)
                    .where(Tweet.id == tweet.id)
                    .values(processed_for_sentiment=True)
                )
                
                processed_count += 1
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error processing tweet {tweet.tweet_id}: {e}")
                await session.rollback()
        
        logger.info(f"Sentiment analysis complete - {processed_count} tweets processed")


if __name__ == "__main__":
    asyncio.run(process_tweets())

