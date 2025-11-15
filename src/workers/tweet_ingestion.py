"""Tweet ingestion worker - fetches recent tweets for configured influencers."""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import re

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet
from src.services.config import settings
from src.services.logging import setup_logging, logger
from src.services.x_api_client import x_api_client


async def fetch_tweets_from_x_api(handle: str, since: datetime) -> List[dict]:
    """
    Fetch recent tweets for an influencer from X API.
    
    Args:
        handle: Influencer X handle (without @)
        since: Fetch tweets since this datetime
        
    Returns:
        List of tweet dicts with id, text, created_at
    """
    if not settings.x_api_bearer_token:
        logger.warning("X_API_BEARER_TOKEN not configured - skipping tweet fetch")
        return []
    
    # Calculate hours since
    hours_since = int((datetime.utcnow() - since).total_seconds() / 3600)
    
    # Fetch tweets using X API client
    tweets = await x_api_client.get_user_tweets(
        username=handle,
        max_results=100,  # Fetch up to 100 recent tweets
        since_hours=hours_since
    )
    
    return tweets


def detect_asset_symbols(tweet_text: str) -> List[str]:
    """
    Detect which assets (BTC, GOLD, SPX) are referenced in tweet text.
    
    Args:
        tweet_text: Tweet text to analyze
        
    Returns:
        List of asset symbols found
    """
    assets = []
    text_upper = tweet_text.upper()
    
    # BTC patterns
    if re.search(r'\bBTC\b|\bBITCOIN\b', text_upper):
        assets.append("BTC")
    
    # Gold patterns
    if re.search(r'\bGOLD\b|\bGLD\b|\bXAU\b', text_upper):
        assets.append("GOLD")
    
    # S&P 500 patterns
    if re.search(r'\bSPX\b|\bSPY\b|\bS&P\s*500\b|\bS&P500\b', text_upper):
        assets.append("SPX")
    
    return assets


async def ingest_tweets():
    """Main ingestion logic - fetch and store new tweets."""
    setup_logging()
    logger.info("Starting tweet ingestion worker")
    
    async with AsyncSessionLocal() as session:
        # Get all influencers
        result = await session.execute(select(Influencer))
        influencers = result.scalars().all()
        
        if not influencers:
            logger.warning("No influencers found in database")
            return
        
        # Fetch tweets from last 24 hours (configurable)
        since = datetime.utcnow() - timedelta(days=1)
        
        total_new = 0
        for influencer in influencers:
            logger.info(f"Fetching tweets for {influencer.handle}")
            
            try:
                # Fetch from X API
                raw_tweets = await fetch_tweets_from_x_api(influencer.handle, since)
                
                for raw_tweet in raw_tweets:
                    # Detect referenced assets
                    asset_symbols = detect_asset_symbols(raw_tweet["text"])
                    
                    if not asset_symbols:
                        logger.debug(f"Skipping tweet {raw_tweet['id']} - no assets detected")
                        continue
                    
                    # Insert tweet (on conflict do nothing - idempotent)
                    stmt = insert(Tweet).values(
                        influencer_id=influencer.id,
                        tweet_id=str(raw_tweet["id"]),
                        text=raw_tweet["text"],
                        tweeted_at=raw_tweet["created_at"],
                        asset_symbols=asset_symbols,
                        ingested_at=datetime.utcnow(),
                        processed_for_sentiment=False,
                    ).on_conflict_do_nothing(index_elements=["tweet_id"])
                    
                    result = await session.execute(stmt)
                    if result.rowcount > 0:
                        total_new += 1
                        logger.info(
                            f"Ingested tweet {raw_tweet['id']} from {influencer.handle} "
                            f"(assets: {', '.join(asset_symbols)})"
                        )
                
                await session.commit()
            except Exception as e:
                logger.error(f"Error fetching tweets for {influencer.handle}: {e}")
                await session.rollback()
        
        logger.info(f"Tweet ingestion complete - {total_new} new tweets ingested")


if __name__ == "__main__":
    asyncio.run(ingest_tweets())

