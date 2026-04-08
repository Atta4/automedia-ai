import asyncio
import random
import time
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from core.models import TopicSource, SourceType
from config.settings import get_settings

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


def _make_pytrends():
    """
    Create TrendReq compatible with both urllib3 v1 and v2.
    urllib3 v2 removed 'method_whitelist' — we avoid passing retries
    through pytrends and handle retries ourselves via tenacity.
    """
    from pytrends.request import TrendReq
    return TrendReq(
        hl="en-US",
        tz=360,
        timeout=(10, 30),
        # Do NOT pass retries= here — causes method_whitelist crash on urllib3 v2
        requests_args={
            "headers": {
                "User-Agent": random.choice(_USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        },
    )


class GoogleTrendsScraper:

    def __init__(self):
        self.settings = get_settings()

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(min=5, max=30))
    async def get_trending_searches(self, region: str | None = None) -> list[dict]:
        region = region or self.settings.trending_region
        logger.info(f"Fetching Google Trends for region: {region}")

        loop = asyncio.get_event_loop()

        def _fetch():
            pt = _make_pytrends()
            time.sleep(random.uniform(1.5, 3.0))
            return pt.trending_searches(pn=region.lower())

        try:
            df = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.warning(f"Google Trends failed: {e} — retrying...")
            raise

        topics = []
        for idx, row in df.iterrows():
            keyword = str(row[0]).strip()
            if not keyword:
                continue
            score = max(100 - (idx * 2), 10)
            source = TopicSource(
                source_type=SourceType.GOOGLE_TRENDS,
                title=keyword,
                snippet=f"Trending on Google ({region})",
                engagement_score=float(score),
            )
            topics.append({"keyword": keyword, "source": source, "rank": idx + 1})

        logger.success(f"Google Trends → {len(topics)} topics fetched")
        return topics

    async def get_related_queries(self, keyword: str) -> list[str]:
        loop = asyncio.get_event_loop()

        def _fetch():
            pt = _make_pytrends()
            time.sleep(random.uniform(1.0, 2.0))
            pt.build_payload([keyword], cat=0, timeframe="now 1-d")
            related = pt.related_queries()
            rising = related.get(keyword, {}).get("rising")
            if rising is not None and not rising.empty:
                return rising["query"].tolist()[:5]
            return []

        try:
            return await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.warning(f"Related queries failed for '{keyword}': {e}")
            return []