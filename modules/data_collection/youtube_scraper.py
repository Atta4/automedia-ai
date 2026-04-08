import asyncio
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from core.models import TopicSource, SourceType
from config.settings import get_settings


class YouTubeScraper:
    """
    Searches YouTube for videos related to a topic keyword.
    Extracts transcripts from top results as reference material for script generation.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.youtube_api_key
        self._yt_client = None

    def _get_client(self):
        if not self._yt_client and self.api_key:
            self._yt_client = build("youtube", "v3", developerKey=self.api_key)
        return self._yt_client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def search_videos(self, keyword: str, max_results: int = 5) -> list[dict]:
        """
        Search YouTube for videos matching keyword.
        Returns list of {video_id, title, view_count, url} dicts.
        """
        client = self._get_client()
        if not client:
            logger.warning("YOUTUBE_API_KEY not set — skipping YouTube search")
            return []

        logger.info(f"YouTube searching: '{keyword}'")

        loop = asyncio.get_event_loop()

        def _search():
            return client.search().list(
                q=keyword,
                part="snippet",
                type="video",
                maxResults=max_results,
                order="viewCount",
                relevanceLanguage=self.settings.content_language,
                videoDuration="medium",       # 4–20 min videos
            ).execute()

        response = await loop.run_in_executor(None, _search)
        items = response.get("items", [])

        results = []
        for item in items:
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            results.append({
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

        logger.success(f"YouTube → {len(results)} videos for '{keyword}'")
        return results

    async def get_transcript(self, video_id: str) -> str | None:
        """
        Extract auto-generated or manual transcript from a YouTube video.
        Returns cleaned plain text or None if unavailable.
        """
        loop = asyncio.get_event_loop()

        def _fetch():
            try:
                # Use list() method instead of get_transcript() for newer API versions
                transcript_list = YouTubeTranscriptApi.list_transcripts(
                    video_id=video_id
                )
                
                # Try to get transcript in preferred language
                try:
                    transcript = transcript_list.find_generated_transcript([
                        self.settings.content_language, 
                        'en', 
                        'ur',
                        'ar'
                    ])
                except:
                    # Fallback to any available transcript
                    transcript = next(iter(transcript_list))
                
                transcript_data = transcript.fetch()
                
                # Join all segments into one clean text blob
                text = " ".join(
                    seg["text"].replace("\n", " ").replace("  ", " ")
                    for seg in transcript_data
                )
                return text.strip()
            except (NoTranscriptFound, TranscriptsDisabled, StopIteration):
                return None
            except Exception as e:
                logger.warning(f"Transcript error for {video_id}: {e}")
                return None

        return await loop.run_in_executor(None, _fetch)

    async def scrape_topic(
        self, keyword: str, max_videos: int = 3
    ) -> tuple[list[TopicSource], list[str]]:
        """
        High-level method: search videos + extract transcripts.
        Returns (sources_for_validation, transcript_texts).
        """
        videos = await self.search_videos(keyword, max_results=max_videos + 2)

        sources: list[TopicSource] = []
        transcripts: list[str] = []

        for video in videos[:max_videos]:
            video_id = video["video_id"]

            source = TopicSource(
                source_type=SourceType.YOUTUBE,
                url=video["url"],
                title=video["title"],
                snippet=f"YouTube video by {video['channel']}",
                engagement_score=75.0,
            )
            sources.append(source)

            # Extract transcript asynchronously
            transcript = await self.get_transcript(video_id)
            if transcript:
                # Truncate to ~1000 words to avoid token bloat in later LLM calls
                words = transcript.split()
                truncated = " ".join(words[:1000])
                transcripts.append(truncated)
                logger.debug(f"Transcript extracted: {video_id} ({len(words)} words)")

        logger.success(
            f"YouTube scrape complete for '{keyword}': "
            f"{len(sources)} sources, {len(transcripts)} transcripts"
        )
        return sources, transcripts
