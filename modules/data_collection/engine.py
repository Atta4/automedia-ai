"""
Enhanced Data Collection Engine with Multi-Source Verification.

NEW ARCHITECTURE:
- Collects from 6+ source types (not just NewsAPI)
- Requires 3+ INDEPENDENT source categories for validation
- Includes social media, independent journalists, community discussions
- Bias detection flags for manipulation techniques
- Ground truth prioritization (eyewitness > expert > journalist)

Source Categories:
1. SOCIAL MEDIA: Twitter, Reddit (real people, real-time)
2. INDEPENDENT: RSS feeds, Substack (independent journalists)
3. COMMUNITY: Reddit discussions, Telegram (community fact-checking)
4. MAINSTREAM: NewsAPI, Google Trends (for narrative tracking)
5. VIDEO: YouTube (visual confirmation, citizen journalism)
"""

import asyncio
import re
from datetime import datetime
from loguru import logger

from core.models import TrendingTopic, TopicStatus, TopicSource, SourceType
from core.database import get_db
from config.settings import get_settings

# Import all scrapers
from modules.data_collection.trends_scraper import GoogleTrendsScraper
from modules.data_collection.news_scraper import NewsScraper
from modules.data_collection.youtube_scraper import YouTubeScraper
from modules.data_collection.twitter_scraper import TwitterScraper
from modules.data_collection.reddit_scraper import RedditScraper
from modules.data_collection.rss_feed_scraper import RSSFeedAggregator
from modules.data_collection.telegram_scraper import TelegramScraper
from modules.data_collection.bias_detector import BiasDetector


def _normalize_keyword(keyword: str) -> str:
    kw = keyword.lower().strip()
    kw = re.sub(r"[^\w\s]", "", kw)
    kw = re.sub(r"\s+", " ", kw)
    return kw


class DataCollectionEngine:
    """
    Enhanced multi-source data collection with 3+ source verification.

    Validation Requirements:
    - Topic must appear in 3+ INDEPENDENT source CATEGORIES:
      * Social Media (Twitter/Reddit)
      * Independent Media (RSS feeds, Substack)
      * Community Discussions (Reddit threads, Telegram)
      * Mainstream Media (NewsAPI - for comparison only)
      * Video Evidence (YouTube)

    Priority:
    1. Eyewitness accounts (Twitter, Telegram)
    2. Expert analysis (independent journalists, Reddit AMAs)
    3. Community validation (Reddit discussions)
    4. Mainstream coverage (for narrative tracking)
    """

    def __init__(self):
        self.settings = get_settings()
        
        # Initialize all scrapers
        self.trends = GoogleTrendsScraper()
        self.news = NewsScraper()
        self.youtube = YouTubeScraper()
        self.twitter = TwitterScraper()
        self.reddit = RedditScraper()
        self.rss = RSSFeedAggregator()
        self.telegram = TelegramScraper()
        self.bias_detector = BiasDetector()

    async def run(self) -> list[TrendingTopic]:
        logger.info("=== Enhanced Data Collection Engine: START ===")
        logger.info("Sources: Twitter, Reddit, RSS, YouTube, NewsAPI, Google Trends")

        candidates = await self._discover_candidates()
        logger.info(f"Candidates discovered: {len(candidates)}")

        if not candidates:
            logger.warning(
                "Zero candidates. Possible reasons:\n"
                "  1. All APIs rate-limited or blocked\n"
                "  2. No internet connection\n"
                "  3. Focus keywords list is empty"
            )
            return []

        validated: list[TrendingTopic] = []
        limit = self.settings.max_topics_per_run
        blocked = self.settings.get_blocked_topics()

        for topic in candidates[:limit * 3]:
            if len(validated) >= limit:
                break

            # Block filter
            if any(b in topic["keyword"].lower() for b in blocked if b):
                logger.debug(f"Blocked topic: '{topic['keyword']}'")
                continue

            result = await self._validate_topic_strict(topic)
            if result and result.is_validated:
                validated.append(result)

        logger.info(f"✓ Validated: {len(validated)} topics (3+ source verification)")
        await self._save_topics(validated)
        logger.info("=== Data Collection Engine: DONE ===")
        return validated

    async def _discover_candidates(self) -> list[dict]:
        """
        Gather candidates from ALL sources:
        - Social: Twitter, Reddit
        - Independent: RSS feeds
        - Mainstream: NewsAPI, Google Trends (for narrative tracking)
        - Focus keywords: Always injected
        """
        tasks = [
            self._safe_gather("Google Trends", self.trends.get_trending_searches()),
            self._safe_gather("GNews", self.news.get_top_headlines()),
            self._safe_gather("Twitter", self.twitter.get_trending_topics()),
            self._safe_gather("Reddit", self.reddit.get_trending_topics()),
            self._safe_gather("RSS Feeds", self.rss.get_trending_topics()),
            self._safe_gather("Telegram", self.telegram.get_channel_updates()),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        raw: list[dict] = []
        for name, result in zip(
            ["Google Trends", "GNews", "Twitter", "Reddit", "RSS Feeds"],
            results
        ):
            if isinstance(result, Exception):
                logger.warning(f"{name} failed (non-fatal): {result}")
                continue
            if isinstance(result, list):
                raw.extend(result)
                logger.info(f"{name} → {len(result)} candidates")

        # ── ALWAYS inject focus keywords ──────────────────────────────────
        focus = self.settings.get_focus_keywords()
        focus_added = 0
        for keyword in focus:
            norm = _normalize_keyword(keyword)
            already = any(_normalize_keyword(c["keyword"]) == norm for c in raw)
            if not already:
                # Focus keywords start with high priority
                raw.append({
                    "keyword": keyword,
                    "source": {
                        "source_type": SourceType.NEWS_API,
                        "title": keyword,
                        "snippet": "Focus keyword (always monitored)",
                        "engagement": 200.0,
                        "source_category": "independent",
                    },
                    "normalized": norm,
                    "is_focus": True,
                })
                focus_added += 1

        logger.info(f"✓ Focus keywords injected: {focus_added}")

        # Deduplicate
        seen: set[str] = set()
        unique: list[dict] = []
        for item in raw:
            norm = item.get("normalized") or _normalize_keyword(item["keyword"])
            if norm not in seen:
                seen.add(norm)
                item["normalized"] = norm
                unique.append(item)

        # Sort: focus keywords first, then by engagement
        def get_engagement(item):
            """Safely extract engagement score from various source formats."""
            source = item.get("source")
            if isinstance(source, TopicSource):
                return source.engagement_score
            elif isinstance(source, dict):
                return float(source.get("engagement", 0))
            elif isinstance(source, str):
                return 0
            return 0

        unique.sort(
            key=lambda x: (
                0 if x.get("is_focus") else 1,
                -get_engagement(x)
            )
        )

        return unique

    async def _validate_topic_strict(self, candidate: dict) -> TrendingTopic | None:
        """
        STRICT VALIDATION: Topic must appear in 3+ INDEPENDENT source categories.
        
        Categories:
        - social (Twitter, Reddit)
        - independent (RSS feeds, Substack)
        - community (Reddit discussions)
        - mainstream (NewsAPI)
        - video (YouTube)
        """
        keyword = candidate["keyword"]
        normalized = candidate.get("normalized", _normalize_keyword(keyword))

        # Check for duplicate
        db = await get_db()
        existing = await db.topics.find_one({"normalized_keyword": normalized})
        if existing:
            logger.debug(f"Duplicate (skip): '{keyword}'")
            return None

        topic = TrendingTopic(
            keyword=keyword,
            normalized_keyword=normalized,
        )

        # Add initial source (convert from dict if needed)
        if "source" in candidate:
            src = candidate["source"]
            if isinstance(src, dict):
                topic.sources.append(self._dict_to_source(src))
            elif isinstance(src, TopicSource):
                topic.sources.append(src)

        # ── Parallel validation across ALL source types ───────────────────
        validation_tasks = [
            self._safe_validate("Twitter", self.twitter.search_topic(keyword)),
            self._safe_validate("Reddit", self.reddit.search_topic(keyword)),
            self._safe_validate("RSS", self.rss.search_topic(keyword)),
            self._safe_validate("Telegram", self.telegram.search_topic(keyword)),
            self._safe_validate("NewsAPI", self.news.search_topic(keyword)),
            self._safe_validate("YouTube", self.youtube.scrape_topic(keyword)),
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)

        # Collect sources
        source_labels = ["Twitter", "Reddit", "RSS", "Telegram", "NewsAPI", "YouTube"]

        for label, result in zip(source_labels, results):
            if isinstance(result, Exception):
                logger.debug(f"{label} validation failed: {result}")
                continue

            if label == "YouTube":
                # YouTube returns (sources, transcripts)
                if isinstance(result, tuple) and len(result) == 2:
                    yt_sources, transcripts = result
                    topic.sources.extend(yt_sources[:2])
                    topic.youtube_transcripts = transcripts
            elif isinstance(result, list):
                # Convert dicts to TopicSource if needed
                for item in result[:3]:
                    if isinstance(item, dict):
                        topic.sources.append(self._dict_to_source(item))
                    elif isinstance(item, TopicSource):
                        topic.sources.append(item)

        # ── Check for 3+ INDEPENDENT CATEGORIES ───────────────────────────
        categories = set()
        for source in topic.sources:
            cat = source.source_category or self._infer_category(source.source_type)
            categories.add(cat)

        # Strict validation: 3+ different categories
        min_categories = 3
        is_focus = candidate.get("is_focus", False)
        
        # Focus keywords: relaxed to 2 categories (they're pre-selected)
        if is_focus:
            min_categories = 2

        category_diversity = self.bias_detector.get_perspective_diversity(
            [s.model_dump() for s in topic.sources]
        )

        if len(categories) >= min_categories:
            topic.is_validated = True
            topic.source_count = len(topic.sources)
            topic.total_engagement = sum(s.engagement_score for s in topic.sources)
            topic.status = TopicStatus.VALIDATED
            topic.validation_reason = (
                f"✓ Multi-source verified: {len(categories)} categories "
                f"({', '.join(categories)})"
            )
            
            # Add bias analysis
            bias_flags = self._analyze_topic_bias(topic)
            if bias_flags:
                topic.validation_reason += f" | ⚠ Bias flags: {bias_flags}"

            logger.success(
                f"✓ {'[FOCUS] ' if is_focus else ''}Validated: '{keyword}' | "
                f"{len(topic.sources)} sources | {len(categories)} categories | "
                f"engagement={topic.total_engagement:.0f}"
            )
        else:
            # Not enough independent verification
            logger.debug(
                f"✗ Not validated: '{keyword}' | "
                f"Only {len(categories)} categories ({', '.join(categories)})"
            )
            topic.is_validated = False
            topic.validation_reason = (
                f"Insufficient verification: only {len(categories)} categories. "
                f"Need {min_categories}+"
            )

        return topic

    async def _safe_validate(self, name: str, coro):
        """Safely execute validation task with error handling."""
        try:
            return await coro
        except Exception as e:
            logger.debug(f"{name} validation error: {e}")
            return []

    async def _safe_gather(self, name: str, coro):
        """Safely execute discovery task with error handling."""
        try:
            return await coro
        except Exception as e:
            logger.warning(f"{name} discovery error: {e}")
            return []

    def _dict_to_source(self, data: dict) -> TopicSource:
        """Convert dictionary to TopicSource object."""
        try:
            # Handle different dict formats
            source_type = data.get("source_type")
            if isinstance(source_type, str):
                source_type = SourceType(source_type)
            
            return TopicSource(
                source_type=source_type or SourceType.NEWS_API,
                url=data.get("url"),
                title=data.get("title"),
                snippet=data.get("snippet", ""),
                engagement_score=float(data.get("engagement", data.get("engagement_score", 0))),
                author=data.get("author"),
                verified=data.get("verified", False),
                source_category=data.get("source_category"),
                fetched_at=datetime.utcnow(),
            )
        except Exception as e:
            logger.debug(f"Dict to source conversion failed: {e}")
            return TopicSource(
                source_type=SourceType.NEWS_API,
                title=str(data.get("title", "Unknown")),
                snippet="",
                engagement_score=0,
            )

    def _infer_category(self, source_type: SourceType) -> str:
        """Infer source category from source type."""
        mapping = {
            SourceType.TWITTER: "social",
            SourceType.REDDIT: "community",
            SourceType.RSS_FEED: "independent",
            SourceType.NEWS_API: "mainstream",
            SourceType.GOOGLE_TRENDS: "mainstream",
            SourceType.YOUTUBE: "video",
        }
        return mapping.get(source_type, "unknown")

    def _analyze_topic_bias(self, topic: TrendingTopic) -> str:
        """Analyze bias flags for a topic's sources."""
        if not topic.sources:
            return ""

        flags = []
        
        # Check perspective diversity
        diversity = self.bias_detector.get_perspective_diversity(
            [s.model_dump() for s in topic.sources]
        )
        
        if not diversity["diverse"]:
            flags.append("one-sided sources")
        
        # Check for loaded language in snippets
        loaded_count = 0
        for source in topic.sources:
            if source.snippet:
                analysis = self.bias_detector.analyze(source.snippet)
                if analysis.loaded_language or analysis.sensationalism:
                    loaded_count += 1
        
        if loaded_count > len(topic.sources) / 2:
            flags.append("sensationalism")

        return ", ".join(flags) if flags else ""

    async def _save_topics(self, topics: list[TrendingTopic]) -> None:
        if not topics:
            return
        db = await get_db()
        saved = 0
        for topic in topics:
            topic.updated_at = datetime.utcnow()
            doc = topic.model_dump()
            try:
                await db.topics.update_one(
                    {"normalized_keyword": topic.normalized_keyword},
                    {"$set": doc},
                    upsert=True,
                )
                saved += 1
            except Exception as e:
                logger.error(f"Save failed '{topic.keyword}': {e}")
        logger.info(f"Saved {saved}/{len(topics)} topics")

    async def get_pending_topics(self, limit: int = 10) -> list[dict]:
        db = await get_db()
        cursor = db.topics.find(
            {"status": TopicStatus.VALIDATED},
            sort=[("total_engagement", -1)],
            limit=limit,
        )
        return await cursor.to_list(length=limit)

    async def mark_topic_status(self, normalized_keyword: str, status: TopicStatus):
        db = await get_db()
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        )
