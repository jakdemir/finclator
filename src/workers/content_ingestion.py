"""Content ingestion worker — orchestrates YouTube + Grok + Gemini stance pipeline."""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.db.session import AsyncSessionLocal
from src.db.models import Influencer, Tweet, SentimentPrediction, Direction, Horizon
from src.services.config import settings
from src.services.logging import setup_logging
from src.services.youtube_client import fetch_channel_transcripts
from src.services.grok_client import summarize_influencer_tweets
from src.services.stance_extractor import extract_stances

logger = logging.getLogger("finclator.content_ingestion")

# Path to influencer definitions
_INFLUENCERS_V2_PATH = Path(__file__).parent.parent.parent / "data" / "influencers_v2.json"

# Map stance horizon strings to DB enum + maturity deltas
_HORIZON_MAP: dict[str, tuple[Horizon, timedelta]] = {
    "SHORT": (Horizon.SHORT, timedelta(days=7)),
    "MEDIUM": (Horizon.MEDIUM, timedelta(days=30)),
    "LONG": (Horizon.LONG, timedelta(days=90)),
}

# Map stance direction strings to DB enum
_DIRECTION_MAP: dict[str, Direction] = {
    "BUY": Direction.BUY,
    "SELL": Direction.SELL,
    "NEUTRAL": Direction.NEUTRAL,
}


def _load_influencers_v2() -> list[dict[str, Any]]:
    """Load influencer definitions from data/influencers_v2.json."""
    with open(_INFLUENCERS_V2_PATH) as f:
        return json.load(f)


async def _fetch_youtube(influencer: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch YouTube transcripts for an influencer if they have a channel."""
    youtube_handle = influencer.get("sources", {}).get("youtube")
    if not youtube_handle:
        logger.info(f"No YouTube source for {influencer['handle']}, skipping")
        return []

    try:
        return await fetch_channel_transcripts(
            youtube_handle=youtube_handle,
            language=influencer.get("language", "en"),
        )
    except Exception as e:
        logger.error(f"YouTube fetch failed for {influencer['handle']}: {e}")
        return []


async def _fetch_twitter_summary(influencer: dict[str, Any]) -> dict[str, Any] | None:
    """Fetch Grok Twitter summary for an influencer if they have a Twitter handle."""
    twitter_handle = influencer.get("sources", {}).get("twitter")
    if not twitter_handle:
        logger.info(f"No Twitter source for {influencer['handle']}, skipping")
        return None

    if not settings.xai_api_key:
        logger.warning("XAI_API_KEY not configured, skipping Twitter summary")
        return None

    try:
        return await summarize_influencer_tweets(
            twitter_handle=twitter_handle,
            asset_symbols=influencer.get("assets", []),
            language=influencer.get("language", "en"),
        )
    except Exception as e:
        logger.error(f"Grok summary failed for {influencer['handle']}: {e}")
        return None


async def _create_placeholder_tweet(
    session: Any,
    influencer_db: Influencer,
    source_tag: str,
) -> uuid.UUID:
    """
    Create a placeholder Tweet record to attach SentimentPredictions to.

    The existing schema requires predictions to link to a Tweet. We create a
    synthetic tweet record that represents the aggregated content source.

    Args:
        session: DB session
        influencer_db: Influencer ORM object
        source_tag: Source identifier (e.g. "content_ingestion_2025-02-11")

    Returns:
        UUID of the created/existing tweet record
    """
    now = datetime.utcnow()
    tweet_id_str = f"content_{influencer_db.handle}_{now.strftime('%Y%m%d_%H%M')}"

    stmt = insert(Tweet).values(
        id=uuid.uuid4(),
        influencer_id=influencer_db.id,
        tweet_id=tweet_id_str,
        text=f"[Synthetic] Content ingestion for {influencer_db.handle} on {now.strftime('%Y-%m-%d')}",
        tweeted_at=now,
        asset_symbols=[],
        ingested_at=now,
        processed_for_sentiment=True,
    ).on_conflict_do_nothing(index_elements=["tweet_id"]).returning(Tweet.id)

    result = await session.execute(stmt)
    row = result.first()

    if row:
        return row[0]

    # If conflict (already exists), fetch it
    existing = await session.execute(
        select(Tweet.id).where(Tweet.tweet_id == tweet_id_str)
    )
    return existing.scalar_one()


async def _store_stances(
    session: Any,
    influencer_db: Influencer,
    stances: dict[str, Any],
) -> int:
    """
    Convert extracted stances to SentimentPrediction records.

    Args:
        session: DB session
        influencer_db: Influencer ORM object
        stances: Stance extraction result dict

    Returns:
        Number of predictions created
    """
    now = datetime.utcnow()
    count = 0

    # Create placeholder tweet for this ingestion run
    tweet_uuid = await _create_placeholder_tweet(session, influencer_db, "content_ingestion")

    for stance in stances.get("stances", []):
        direction_str = stance.get("direction", "NEUTRAL")
        horizon_str = stance.get("horizon", "MEDIUM")
        conviction = float(stance.get("conviction", 0.5))

        direction = _DIRECTION_MAP.get(direction_str, Direction.NEUTRAL)
        horizon, maturity_delta = _HORIZON_MAP.get(horizon_str, (Horizon.MEDIUM, timedelta(days=30)))

        prediction = SentimentPrediction(
            id=uuid.uuid4(),
            tweet_id=tweet_uuid,
            asset_symbol=stance.get("asset_symbol", "BTC"),
            direction=direction,
            horizon=horizon,
            model_version=f"content_pipeline_v2/{settings.stance_extraction_model}",
            confidence=min(conviction, 0.99),  # DB column is Numeric(3,2)
            created_at=now,
            matures_at=now + maturity_delta,
            evaluated=False,
        )
        session.add(prediction)
        count += 1

    return count


async def ingest_content():
    """
    Main content ingestion pipeline.

    For each influencer in influencers_v2.json:
    1. Fetch YouTube transcripts
    2. Get Grok Twitter summary
    3. Extract stances via Gemini
    4. Store as SentimentPrediction records
    """
    setup_logging()
    logger.info("Starting content ingestion pipeline")

    # Load influencer definitions
    influencers = _load_influencers_v2()
    logger.info(f"Loaded {len(influencers)} influencers from {_INFLUENCERS_V2_PATH}")

    async with AsyncSessionLocal() as session:
        for inf in influencers:
            handle = inf["handle"]
            logger.info(f"--- Processing {handle} ({inf['display_name']}) ---")

            # Step 1: Fetch content (YouTube + Twitter in parallel)
            youtube_task = _fetch_youtube(inf)
            twitter_task = _fetch_twitter_summary(inf)
            youtube_transcripts, twitter_summary = await asyncio.gather(
                youtube_task, twitter_task
            )

            if not youtube_transcripts and not twitter_summary:
                logger.warning(f"No content fetched for {handle}, skipping stance extraction")
                continue

            logger.info(
                f"Content for {handle}: "
                f"{len(youtube_transcripts)} YouTube transcripts, "
                f"Twitter summary: {'yes' if twitter_summary else 'no'}"
            )

            # Step 2: Extract stances via Gemini
            try:
                stances = await extract_stances(
                    handle=handle,
                    display_name=inf["display_name"],
                    finance_school=inf["finance_school"],
                    assets=inf["assets"],
                    language=inf.get("language", "en"),
                    youtube_transcripts=youtube_transcripts,
                    twitter_summary=twitter_summary,
                )
            except Exception as e:
                logger.error(f"Stance extraction failed for {handle}: {e}")
                continue

            # Step 3: Store predictions in DB
            try:
                # Look up influencer in DB
                result = await session.execute(
                    select(Influencer).where(Influencer.handle == handle)
                )
                influencer_db = result.scalar_one_or_none()

                if not influencer_db:
                    logger.warning(
                        f"Influencer {handle} not found in DB, "
                        f"skipping prediction storage (run seed first)"
                    )
                    # Still log the stances for debugging
                    logger.info(f"Extracted stances (not stored): {json.dumps(stances, indent=2)}")
                    continue

                count = await _store_stances(session, influencer_db, stances)
                await session.commit()
                logger.info(f"Stored {count} predictions for {handle}")

            except Exception as e:
                logger.error(f"Failed to store predictions for {handle}: {e}")
                await session.rollback()

    logger.info("Content ingestion pipeline complete")


if __name__ == "__main__":
    asyncio.run(ingest_content())
