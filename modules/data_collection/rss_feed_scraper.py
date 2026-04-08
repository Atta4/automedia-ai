"""
RSS Feed Aggregator for independent journalists and alternative media.

Collects from:
- Substack writers
- Independent journalists
- Alternative media outlets
- Expert newsletters
- Local news sources

This provides narratives outside mainstream corporate media.
"""

import asyncio
import feedparser
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from loguru import logger

from core.models import TopicSource, SourceType
from config.settings import get_settings


# Default independent media RSS feeds
# Users can customize this in settings
INDEPENDENT_FEEDS = [
    # Geopolitics / International
    {
        "name": "The Intercept",
        "url": "https://theintercept.com/feed/",
        "category": "independent",
    },
    {
        "name": "Common Dreams",
        "url": "https://www.commondreams.org/rss.xml",
        "category": "independent",
    },
    {
        "name": "Consortium News",
        "url": "https://consortiumnews.com/feed/",
        "category": "independent",
    },
    # Substack (popular independent writers)
    {
        "name": "Matt Taibbi",
        "url": "https://matttaibbi.substack.com/feed",
        "category": "independent",
    },
    {
        "name": "Glenn Greenwald",
        "url": "https://systemupdate.substack.com/feed",
        "category": "independent",
    },
    {
        "name": "The Grayzone",
        "url": "https://thegrayzone.com/feed/",
        "category": "independent",
    },
    # Regional (Pakistan/India focused)
    {
        "name": "Dawn (Pakistan)",
        "url": "https://www.dawn.com/rss",
        "category": "mainstream",
    },
    {
        "name": "The Wire (India)",
        "url": "https://thewire.in/feed",
        "category": "independent",
    },
    # Middle East focused
    {
        "name": "MintPress News",
        "url": "https://www.mintpressnews.com/feed/",
        "category": "independent",
    },
    {
        "name": "Middle East Eye",
        "url": "https://www.middleeasteye.net/rss",
        "category": "independent",
    },
]


class RSSFeedAggregator:
    """
    Aggregates news from independent journalists and alternative media.
    
    Advantages:
    - Direct from journalists (no editorial filter)
    - Diverse perspectives
    - Often breaks stories mainstream ignores
    - Expert analysis over clickbait
    """

    def __init__(self):
        self.settings = get_settings()
        self.feeds = self._load_feeds()

    def _load_feeds(self) -> list[dict]:
        """Load RSS feeds from settings or use defaults."""
        # In production, users can customize via .env
        # CUSTOM_RSS_FEEDS=feed1|feed2|feed3
        custom_feeds = getattr(self.settings, 'custom_rss_feeds', '')
        
        if custom_feeds:
            return [
                {"name": f"Custom {i}", "url": url.strip(), "category": "independent"}
                for i, url in enumerate(custom_feeds.split('|'))
                if url.strip()
            ]
        
        return INDEPENDENT_FEEDS

    async def get_trending_topics(self, hours: int = 24) -> list[dict]:
        """
        Fetch recent articles from all RSS feeds and extract potential topics.
        """
        candidates = []
        seen_titles = set()

        logger.info(f"RSS: Fetching {len(self.feeds)} independent feeds...")

        async def fetch_feed(feed_info: dict):
            try:
                feed = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: feedparser.parse(feed_info["url"])
                )
                
                if feed.bozo:
                    logger.debug(f"RSS feed error: {feed_info['name']}")
                    return []

                items = []
                for entry in feed.entries[:10]:  # Last 10 posts per feed
                    title = entry.get('title', '')
                    
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    # Calculate engagement (proxy: feed authority + recency)
                    published = self._parse_date(entry.get('published'))
                    hours_old = (datetime.utcnow() - published).total_seconds() / 3600
                    
                    if hours_old > hours * 2:
                        continue

                    # Authority score based on feed reputation
                    authority = 50 if feed_info["category"] == "independent" else 30
                    recency_bonus = max(0, 24 - hours_old)
                    
                    engagement = authority + recency_bonus * 2

                    items.append({
                        "keyword": self._extract_keyword(title),
                        "title": title,
                        "source": feed_info["name"],
                        "url": entry.get('link', ''),
                        "engagement": engagement,
                        "category": feed_info["category"],
                        "published": published,
                    })

                return items

            except Exception as e:
                logger.debug(f"RSS feed failed {feed_info['name']}: {e}")
                return []

        # Fetch all feeds concurrently
        tasks = [fetch_feed(feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                candidates.extend(result)

        # Sort by engagement
        candidates.sort(key=lambda x: x["engagement"], reverse=True)
        
        logger.info(f"RSS: {len(candidates)} articles from {len(self.feeds)} feeds")
        return candidates

    async def search_topic(self, keyword: str, hours: int = 24) -> list[TopicSource]:
        """
        Search through RSS feeds for articles about a specific topic.
        """
        sources = []

        async def search_feed(feed_info: dict):
            try:
                feed = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: feedparser.parse(feed_info["url"])
                )

                for entry in feed.entries[:50]:  # Check last 50 articles
                    title = entry.get('title', '').lower()
                    summary = entry.get('summary', '').lower()
                    
                    # Check if keyword matches
                    if keyword.lower() not in title and keyword.lower() not in summary:
                        continue

                    published = self._parse_date(entry.get('published'))
                    hours_old = (datetime.utcnow() - published).total_seconds() / 3600
                    
                    if hours_old > hours * 2:
                        continue

                    # Engagement based on recency and source type
                    recency_score = max(0, (24 - hours_old) * 3)
                    source_bonus = 30 if feed_info["category"] == "independent" else 15
                    
                    source = TopicSource(
                        source_type=SourceType.RSS_FEED,
                        url=entry.get('link', ''),
                        title=entry.get('title', ''),
                        snippet=entry.get('summary', '')[:280] if entry.get('summary') else "",
                        engagement_score=float(recency_score + source_bonus),
                        author=entry.get('author', feed_info["name"]),
                        verified=False,
                        source_category=feed_info["category"],
                        fetched_at=datetime.utcnow(),
                    )
                    sources.append(source)

            except Exception as e:
                logger.debug(f"RSS search failed {feed_info['name']}: {e}")

        # Search all feeds
        tasks = [search_feed(feed) for feed in self.feeds]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"RSS search '{keyword}': {len(sources)} articles")
        return sources

    def _extract_keyword(self, title: str) -> str:
        """Extract main keyword from article title."""
        # Remove common prefixes
        prefixes = ["Breaking:", "UPDATE:", "Analysis:", "Opinion:"]
        for prefix in prefixes:
            title = title.replace(prefix, "").strip()
        
        # Return first 6-8 words
        words = title.split()[:7]
        return " ".join(words)

    def _parse_date(self, date_str: str) -> datetime:
        """Parse RSS date string to datetime."""
        if not date_str:
            return datetime.utcnow()
        
        try:
            # feedparser parses most RSS date formats
            parsed = feedparser._parse_date(date_str)
            if parsed:
                return datetime(*parsed[:6])
        except Exception:
            pass
        
        return datetime.utcnow()

    async def get_expert_analysis(self, keyword: str) -> list[TopicSource]:
        """
        Find in-depth analysis pieces (longer articles) about a topic.
        """
        sources = []

        for feed_info in self.feeds:
            if feed_info["category"] != "independent":
                continue

            try:
                feed = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: feedparser.parse(feed_info["url"])
                )

                for entry in feed.entries[:30]:
                    title = entry.get('title', '').lower()
                    summary = entry.get('summary', '')
                    
                    if keyword.lower() not in title:
                        continue
                    
                    # Look for longer analysis pieces (500+ words)
                    if len(summary) < 500:
                        continue

                    published = self._parse_date(entry.get('published'))
                    hours_old = (datetime.utcnow() - published).total_seconds() / 3600

                    sources.append(TopicSource(
                        source_type=SourceType.RSS_FEED,
                        url=entry.get('link', ''),
                        title=f"[ANALYSIS] {entry.get('title', '')}",
                        snippet=summary[:280],
                        engagement_score=float(60 + max(0, 24 - hours_old) * 2),
                        author=entry.get('author', feed_info["name"]),
                        verified=True,  # Independent journalists are verified sources
                        source_category="independent",
                        fetched_at=datetime.utcnow(),
                    ))

            except Exception:
                continue

        return sources
