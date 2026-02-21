"""Grok (xAI) client for Twitter/X content summarization."""
import logging
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

from .config import settings

logger = logging.getLogger("finclator.grok")

# xAI Grok API endpoint (OpenAI-compatible)
_XAI_BASE_URL = "https://api.x.ai/v1"
_MODEL = "grok-3-mini-fast"


def _get_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for xAI."""
    if not settings.xai_api_key:
        raise ValueError("XAI_API_KEY not configured")
    return AsyncOpenAI(
        api_key=settings.xai_api_key,
        base_url=_XAI_BASE_URL,
    )


async def summarize_influencer_tweets(
    twitter_handle: str,
    asset_symbols: list[str],
    language: str = "en",
) -> dict[str, Any]:
    """
    Use Grok to summarize an influencer's recent Twitter activity.

    Grok has native X/Twitter context and can see recent tweets without
    needing the Twitter API directly.

    Args:
        twitter_handle: Twitter/X handle (without @)
        asset_symbols: List of asset symbols to focus on (e.g. ["BTC", "GOLD"])
        language: Response language preference

    Returns:
        Dict with keys: handle, summary_text, date_range, asset_symbols
    """
    logger.info(f"Requesting Grok summary for @{twitter_handle} (assets: {asset_symbols})")

    client = _get_client()

    assets_str = ", ".join(asset_symbols)
    lang_instruction = ""
    if language == "tr":
        lang_instruction = (
            "The influencer tweets in Turkish. Summarize in English but preserve "
            "key Turkish financial terms if relevant."
        )

    system_prompt = (
        "You are a financial analyst assistant. Your task is to summarize a Twitter/X "
        "influencer's recent activity and extract their market views. Be factual and specific. "
        "Include any price targets, timeframes, or conviction levels they express."
    )

    user_prompt = (
        f"Summarize the recent Twitter/X activity of @{twitter_handle} regarding these "
        f"assets: {assets_str}.\n\n"
        f"{lang_instruction}\n\n"
        f"Focus on:\n"
        f"1. Their current stance on each asset (bullish/bearish/neutral)\n"
        f"2. Any specific price targets or levels mentioned\n"
        f"3. Their reasoning or thesis\n"
        f"4. Time horizon for their views (short-term days, medium-term weeks, long-term months)\n"
        f"5. How confident or emphatic they seem\n\n"
        f"If they haven't posted about a specific asset recently, say so.\n"
        f"Provide approximate date range of the tweets you're summarizing."
    )

    try:
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        summary_text = response.choices[0].message.content or ""

        result = {
            "handle": twitter_handle,
            "summary_text": summary_text,
            "date_range": f"Recent (as of {datetime.utcnow().strftime('%Y-%m-%d')})",
            "asset_symbols": asset_symbols,
        }

        logger.info(
            f"Grok summary for @{twitter_handle}: {len(summary_text)} chars, "
            f"tokens used: {response.usage.total_tokens if response.usage else 'unknown'}"
        )
        return result

    except Exception as e:
        logger.error(f"Grok API error for @{twitter_handle}: {e}")
        raise
    finally:
        await client.close()
