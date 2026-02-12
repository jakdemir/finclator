"""Stance extraction via Google Gemini Flash."""
import json
import logging
from datetime import datetime
from typing import Any, Optional

import google.generativeai as genai

from .config import settings

logger = logging.getLogger("finclator.stance")


def _configure_gemini() -> None:
    """Configure the Gemini client with API key."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not configured")
    genai.configure(api_key=settings.gemini_api_key)


_EXTRACTION_PROMPT = """\
You are an expert financial analyst. Given the following content from a finance influencer, \
extract their stance on each asset listed.

**Influencer:** {handle} ({display_name})
**Finance School:** {finance_school}
**Assets to analyze:** {assets}
**Language context:** Content may be in {language}

---
**YouTube Transcripts:**
{youtube_content}

---
**Twitter/X Summary:**
{twitter_content}

---

For each asset, determine:
- **direction**: BUY, SELL, or NEUTRAL (based on their expressed view)
- **conviction**: 0.0 to 1.0 (how strongly they feel - emphatic language = higher)
- **horizon**: SHORT (days), MEDIUM (weeks), or LONG (months+)
- **key_thesis**: One sentence summarizing their reasoning
- **price_target**: Numeric target if mentioned, null otherwise
- **sources**: List of source identifiers (e.g. "youtube:VIDEO_ID", "twitter_summary")

If there is insufficient information about an asset, set direction to NEUTRAL with \
conviction 0.3 and note "insufficient data" in key_thesis.

Respond with valid JSON only, in this exact format:
{{
  "influencer_handle": "{handle}",
  "extraction_date": "{date}",
  "stances": [
    {{
      "asset_symbol": "BTC",
      "direction": "BUY",
      "conviction": 0.85,
      "horizon": "MEDIUM",
      "key_thesis": "...",
      "price_target": 150000,
      "sources": ["youtube:abc123", "twitter_summary"]
    }}
  ]
}}
"""


async def extract_stances(
    handle: str,
    display_name: str,
    finance_school: str,
    assets: list[str],
    language: str,
    youtube_transcripts: list[dict[str, Any]],
    twitter_summary: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """
    Extract structured stances from gathered influencer content using Gemini Flash.

    Args:
        handle: Influencer handle
        display_name: Influencer display name
        finance_school: Their finance school/approach
        assets: List of asset symbols to analyze
        language: Content language
        youtube_transcripts: List of transcript dicts from youtube_client
        twitter_summary: Summary dict from grok_client (or None)

    Returns:
        Structured stance extraction dict
    """
    _configure_gemini()

    logger.info(f"Extracting stances for {handle} across {assets}")

    # Format YouTube content
    youtube_parts: list[str] = []
    source_ids: list[str] = []
    for t in youtube_transcripts:
        vid_id = t.get("video_id", "unknown")
        title = t.get("title", "Unknown")
        text = t.get("transcript_text", "")
        date = t.get("published_at")
        date_str = date.strftime("%Y-%m-%d") if date else "unknown date"

        # Truncate very long transcripts to keep within context limits
        if len(text) > 8000:
            text = text[:8000] + "... [truncated]"

        youtube_parts.append(f"### {title} ({date_str}, id: {vid_id})\n{text}")
        source_ids.append(f"youtube:{vid_id}")

    youtube_content = "\n\n".join(youtube_parts) if youtube_parts else "(No YouTube content available)"

    # Format Twitter content
    if twitter_summary and twitter_summary.get("summary_text"):
        twitter_content = (
            f"Date range: {twitter_summary.get('date_range', 'unknown')}\n"
            f"{twitter_summary['summary_text']}"
        )
        source_ids.append("twitter_summary")
    else:
        twitter_content = "(No Twitter summary available)"

    # Build prompt
    prompt = _EXTRACTION_PROMPT.format(
        handle=handle,
        display_name=display_name,
        finance_school=finance_school,
        assets=", ".join(assets),
        language=language,
        youtube_content=youtube_content,
        twitter_content=twitter_content,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
    )

    try:
        model = genai.GenerativeModel(settings.stance_extraction_model)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        # Parse JSON response
        raw_text = response.text
        result = json.loads(raw_text)

        # Validate basic structure
        if "stances" not in result:
            logger.warning(f"Missing 'stances' key in Gemini response for {handle}")
            result = _empty_result(handle, assets)

        logger.info(
            f"Extracted {len(result.get('stances', []))} stances for {handle}: "
            f"{[s.get('asset_symbol') + '=' + s.get('direction', '?') for s in result.get('stances', [])]}"
        )
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini JSON response for {handle}: {e}")
        return _empty_result(handle, assets)
    except Exception as e:
        logger.error(f"Gemini API error for {handle}: {e}")
        raise


def _empty_result(handle: str, assets: list[str]) -> dict[str, Any]:
    """Return a default empty result when extraction fails."""
    return {
        "influencer_handle": handle,
        "extraction_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "stances": [
            {
                "asset_symbol": asset,
                "direction": "NEUTRAL",
                "conviction": 0.0,
                "horizon": "MEDIUM",
                "key_thesis": "Extraction failed - no data available",
                "price_target": None,
                "sources": [],
            }
            for asset in assets
        ],
    }
