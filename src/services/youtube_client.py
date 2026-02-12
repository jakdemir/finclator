"""YouTube transcript ingestion via yt-dlp."""
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

import yt_dlp

from .config import settings

logger = logging.getLogger("finclator.youtube")


# yt-dlp options for fetching subtitles only (no video download)
_BASE_YDL_OPTS: dict[str, Any] = {
    "skip_download": True,
    "writeautomaticsub": True,
    "subtitleslangs": ["tr", "en"],
    "subtitlesformat": "vtt",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
}


def _extract_transcript_text(subtitle_info: dict, lang: str) -> tuple[str, str] | None:
    """
    Extract plain text from subtitle info for a given language.

    Args:
        subtitle_info: yt-dlp subtitle metadata for a single video
        lang: Preferred language code

    Returns:
        Tuple of (transcript_text, language) or None if unavailable
    """
    if not subtitle_info:
        return None

    # Try requested language, then fall back to any available
    auto_subs = subtitle_info.get("automatic_captions", {})
    manual_subs = subtitle_info.get("subtitles", {})

    # Prefer manual subs over auto-generated
    for subs_dict in (manual_subs, auto_subs):
        for try_lang in (lang, "en", "tr"):
            if try_lang in subs_dict:
                formats = subs_dict[try_lang]
                # Find a text-based format (vtt or srv3)
                for fmt in formats:
                    if fmt.get("ext") in ("vtt", "srv3", "json3"):
                        return fmt.get("url", ""), try_lang

    return None


async def _fetch_subtitle_text(url: str) -> str:
    """Download and clean subtitle text from a URL."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.text
    except Exception as e:
        logger.warning(f"Failed to download subtitle from {url}: {e}")
        return ""

    # Strip VTT headers and timestamps, keep only text lines
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        # Skip VTT metadata lines
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        # Skip timestamp lines (e.g. "00:00:01.000 --> 00:00:04.000")
        if "-->" in line:
            continue
        # Skip numeric cue identifiers
        if line.isdigit():
            continue
        # Remove VTT tags like <c> </c> <00:00:01.000>
        import re
        cleaned = re.sub(r"<[^>]+>", "", line)
        if cleaned.strip():
            lines.append(cleaned.strip())

    # Deduplicate consecutive identical lines (VTT often repeats)
    deduped: list[str] = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    return " ".join(deduped)


async def fetch_channel_transcripts(
    youtube_handle: str,
    language: str = "en",
    max_videos: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch recent video transcripts from a YouTube channel.

    Args:
        youtube_handle: YouTube channel handle (e.g. "@santmanukyan")
        language: Preferred subtitle language code
        max_videos: Maximum number of videos to fetch (default from settings)

    Returns:
        List of dicts: [{video_id, title, published_at, transcript_text, language}]
    """
    max_videos = max_videos or settings.youtube_video_limit

    channel_url = f"https://www.youtube.com/{youtube_handle}/videos"
    logger.info(f"Fetching up to {max_videos} transcripts from {channel_url} (lang={language})")

    # Step 1: Get recent video URLs from channel
    flat_opts: dict[str, Any] = {
        "extract_flat": True,
        "playlistend": max_videos,
        "quiet": True,
        "no_warnings": True,
    }

    video_entries: list[dict] = []
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            result = await loop.run_in_executor(None, ydl.extract_info, channel_url, False)

        if result and "entries" in result:
            video_entries = list(result["entries"])[:max_videos]
        else:
            logger.warning(f"No entries found for channel {youtube_handle}")
            return []
    except Exception as e:
        logger.error(f"Failed to list videos for {youtube_handle}: {e}")
        return []

    logger.info(f"Found {len(video_entries)} videos for {youtube_handle}")

    # Step 2: Fetch subtitles for each video
    transcripts: list[dict[str, Any]] = []

    for entry in video_entries:
        video_id = entry.get("id", entry.get("url", ""))
        title = entry.get("title", "Unknown")

        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            sub_opts: dict[str, Any] = {
                **_BASE_YDL_OPTS,
                "subtitleslangs": [language, "en", "tr"],
            }

            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                info = await loop.run_in_executor(None, ydl.extract_info, video_url, False)

            if not info:
                logger.debug(f"No info for video {video_id}")
                continue

            # Try to get subtitle URL
            sub_result = _extract_transcript_text(info, language)
            if not sub_result:
                logger.debug(f"No subtitles available for {video_id} ({title})")
                continue

            sub_url, detected_lang = sub_result
            if not sub_url:
                logger.debug(f"Empty subtitle URL for {video_id}")
                continue

            # Download and parse subtitle text
            transcript_text = await _fetch_subtitle_text(sub_url)
            if not transcript_text:
                logger.debug(f"Empty transcript for {video_id}")
                continue

            # Parse upload date
            upload_date = info.get("upload_date", "")  # format: YYYYMMDD
            published_at: Optional[datetime] = None
            if upload_date and len(upload_date) == 8:
                try:
                    published_at = datetime.strptime(upload_date, "%Y%m%d")
                except ValueError:
                    pass

            transcripts.append({
                "video_id": video_id,
                "title": title,
                "published_at": published_at,
                "transcript_text": transcript_text,
                "language": detected_lang,
            })

            logger.info(
                f"Fetched transcript for {video_id} ({title}) - "
                f"{len(transcript_text)} chars, lang={detected_lang}"
            )

        except Exception as e:
            logger.error(f"Error fetching subtitles for video {video_id}: {e}")
            continue

    logger.info(f"Successfully fetched {len(transcripts)} transcripts for {youtube_handle}")
    return transcripts
