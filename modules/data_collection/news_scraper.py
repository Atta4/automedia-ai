import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from core.models import TopicSource, SourceType
from config.settings import get_settings


class NewsScraper:
    """
    News scraper — supports both NewsAPI.org AND GNews API.

    NewsAPI.org keys:  32-char alphanumeric  e.g. a1b2c3d4e5f6...
    GNews API keys:    UUID format           e.g. 4dc9247d-9dba-4cdc-87d1-3d788fbf5002

    Auto-detects which service to use based on key format.
    """

    # NewsAPI endpoints
    NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"
    NEWSAPI_HEADLINES  = "https://newsapi.org/v2/top-headlines"

    # GNews API endpoints
    GNEWS_SEARCH       = "https://gnews.io/api/v4/search"
    GNEWS_TOP          = "https://gnews.io/api/v4/top-headlines"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.newsapi_key
        self._is_gnews = self._detect_gnews_key()

        if self._is_gnews:
            logger.info("News provider: GNews API (UUID key detected)")
        elif self.api_key:
            logger.info("News provider: NewsAPI.org")
        else:
            logger.warning("No news API key set — news source disabled")

    def _detect_gnews_key(self) -> bool:
        """UUID format = GNews key (e.g. 4dc9247d-9dba-4cdc-87d1-3d788fbf5002)"""
        import re
        if not self.api_key:
            return False
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, self.api_key.lower()))

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_topic(self, keyword: str, max_results: int = 5) -> list[TopicSource]:
        if not self.api_key:
            return []
        if self._is_gnews:
            return await self._gnews_search(keyword, max_results)
        return await self._newsapi_search(keyword, max_results)

    async def get_top_headlines(self, category: str = "general") -> list[dict]:
        if not self.api_key:
            logger.warning("No news API key — skipping headlines")
            return []
        if self._is_gnews:
            return await self._gnews_headlines(category)
        return await self._newsapi_headlines(category)

    # ── GNews implementation ──────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _gnews_search(self, keyword: str, max_results: int) -> list[TopicSource]:
        logger.info(f"GNews searching: '{keyword}'")
        params = {
            "q": keyword,
            "lang": self.settings.content_language,
            "max": min(max_results, 10),
            "apikey": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.GNEWS_SEARCH, params=params)
                if resp.status_code != 200:
                    body = resp.json()
                    logger.warning(f"GNews error {resp.status_code}: {body.get('errors', body)}")
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning(f"GNews search failed: {e}")
            return []

        sources = []
        top_outlets = {"bbc", "cnn", "reuters", "bloomberg", "guardian", "ap"}
        for article in data.get("articles", []):
            title = article.get("title", "")
            if not title:
                continue
            source_name = article.get("source", {}).get("name", "").lower()
            score = 90.0 if any(o in source_name for o in top_outlets) else 65.0
            sources.append(TopicSource(
                source_type=SourceType.NEWS_API,
                url=article.get("url", ""),
                title=title,
                snippet=(article.get("description") or "")[:300],
                engagement_score=score,
            ))

        logger.success(f"GNews → {len(sources)} articles for '{keyword}'")
        return sources

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _gnews_headlines(self, category: str = "general") -> list[dict]:
        logger.info(f"GNews top headlines: category={category}")

        # GNews category mapping
        gnews_categories = {
            "general": "general", "business": "business",
            "technology": "technology", "science": "science",
            "health": "health", "sports": "sports", "entertainment": "entertainment",
        }
        cat = gnews_categories.get(category, "general")

        params = {
            "category": cat,
            "lang": self.settings.content_language,
            "country": self.settings.trending_region.lower(),
            "max": 20,
            "apikey": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.GNEWS_TOP, params=params)
                if resp.status_code != 200:
                    body = resp.json()
                    logger.warning(f"GNews headlines error {resp.status_code}: {body.get('errors', body)}")
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning(f"GNews headlines failed: {e}")
            return []

        topics = []
        for article in data.get("articles", []):
            title = article.get("title", "")
            if not title:
                continue
            words = [w for w in title.split() if len(w) > 3]
            keyword = " ".join(words[:3]) if words else title[:40]
            source = TopicSource(
                source_type=SourceType.NEWS_API,
                url=article.get("url", ""),
                title=title,
                snippet=(article.get("description") or "")[:300],
                engagement_score=70.0,
            )
            topics.append({"keyword": keyword, "source": source})

        logger.success(f"GNews headlines → {len(topics)} topics")
        return topics

    # ── NewsAPI.org implementation ────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _newsapi_search(self, keyword: str, max_results: int) -> list[TopicSource]:
        logger.info(f"NewsAPI searching: '{keyword}'")
        params = {
            "q": keyword,
            "language": self.settings.content_language,
            "sortBy": "publishedAt",
            "pageSize": max_results,
            "apiKey": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.NEWSAPI_EVERYTHING, params=params)
                if resp.status_code != 200:
                    body = resp.json()
                    logger.warning(f"NewsAPI error {resp.status_code}: {body.get('message','unknown')}")
                    if resp.status_code in (401, 403, 426):
                        return []
                    resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"NewsAPI HTTP error: {e}")
            return []

        sources = []
        top_outlets = {"bbc", "cnn", "reuters", "bloomberg", "guardian", "ap", "forbes"}
        for article in data.get("articles", []):
            title = article.get("title", "")
            if not title or title == "[Removed]":
                continue
            source_name = article.get("source", {}).get("name", "").lower()
            score = 90.0 if any(o in source_name for o in top_outlets) else 60.0
            sources.append(TopicSource(
                source_type=SourceType.NEWS_API,
                url=article.get("url", ""),
                title=title,
                snippet=(article.get("description") or "")[:300],
                engagement_score=score,
            ))
        logger.success(f"NewsAPI → {len(sources)} articles for '{keyword}'")
        return sources

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _newsapi_headlines(self, category: str = "general") -> list[dict]:
        params = {
            "category": category,
            "language": self.settings.content_language,
            "country": self.settings.trending_region.lower(),
            "pageSize": 20,
            "apiKey": self.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.NEWSAPI_HEADLINES, params=params)
                if resp.status_code != 200:
                    body = resp.json()
                    logger.warning(f"NewsAPI headlines error {resp.status_code}: {body.get('message','unknown')}")
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning(f"NewsAPI headlines failed: {e}")
            return []

        topics = []
        for article in data.get("articles", []):
            title = article.get("title", "")
            if not title or title == "[Removed]":
                continue
            words = [w for w in title.split() if len(w) > 3]
            keyword = " ".join(words[:3]) if words else title[:40]
            source = TopicSource(
                source_type=SourceType.NEWS_API,
                url=article.get("url", ""),
                title=title,
                snippet=(article.get("description") or "")[:300],
                engagement_score=70.0,
            )
            topics.append({"keyword": keyword, "source": source})

        logger.success(f"NewsAPI headlines → {len(topics)} topics")
        return topics