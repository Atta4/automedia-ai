"""
Twitter/X Scraper for trending topics and public opinions.

Uses Tweepy for official API access or snscrape for no-auth scraping.
Collects: trending hashtags, viral threads, eyewitness accounts, expert opinions.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from core.models import TopicSource, SourceType
from config.settings import get_settings


class TwitterScraper:
    """
    Collects trending topics and public sentiment from Twitter/X.
    
    Sources:
    - Trending hashtags in region
    - Search queries for keywords
    - Verified expert accounts
    - Viral threads (high engagement)
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Twitter API client (tweepy)."""
        try:
            import tweepy
            
            # Twitter API v2 requires bearer token
            twitter_bearer = getattr(self.settings, 'twitter_bearer_token', None)
            
            if not twitter_bearer:
                logger.warning("Twitter API not configured - missing TWITTER_BEARER_TOKEN")
                return None

            self.client = tweepy.Client(
                bearer_token=twitter_bearer,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API client initialized")
            
        except ImportError:
            logger.warning("tweepy not installed - Twitter scraping disabled")
            return None
        except Exception as e:
            logger.warning(f"Twitter API init failed: {e}")
            return None

    async def get_trending_topics(self, region: str = "PK") -> list[dict]:
        """
        Get trending topics from Twitter for a region.
        
        Note: Twitter API free tier doesn't include trends.
        This is a placeholder for premium API or use snscrape alternative.
        """
        if not self.client:
            return await self._fallback_trending(region)

        try:
            # Requires Premium API access
            # trends = self.client.get_place_trends(id=woeid)
            logger.warning("Twitter trends require Premium API - using search fallback")
            return await self._fallback_trending(region)
            
        except Exception as e:
            logger.warning(f"Twitter trends failed: {e}")
            return await self._fallback_trending(region)

    async def search_topic(self, keyword: str, hours: int = 24) -> list[TopicSource]:
        """
        Search Twitter for a specific keyword/topic.
        Collects tweets, engagement metrics, and author info.
        """
        if not self.client:
            return await self._fallback_search(keyword)

        sources = []
        
        try:
            # Search recent tweets (requires API v2)
            query = f"{keyword} -is:retweet lang:en"
            
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=20,
                tweet_fields=[
                    'created_at', 'public_metrics', 'author_id', 'text'
                ],
                user_fields=['verified', 'username', 'name']
            )
            
            if not tweets.data:
                return await self._fallback_search(keyword)

            # Get user info for authors
            user_ids = list(set(tweet.author_id for tweet in tweets.data))
            users = self.client.get_users(
                ids=user_ids,
                user_fields=['verified', 'username', 'name']
            )
            user_map = {u.id: u for u in users.data} if users.data else {}

            for tweet in tweets.data:
                metrics = tweet.public_metrics
                engagement = (
                    metrics.get('retweet_count', 0) * 2 +
                    metrics.get('like_count', 0) +
                    metrics.get('reply_count', 0) * 3 +
                    metrics.get('quote_count', 0) * 2
                )

                user = user_map.get(tweet.author_id)
                is_verified = user.verified if user else False

                source = TopicSource(
                    source_type=SourceType.TWITTER,
                    url=f"https://twitter.com/status/{tweet.id}",
                    title=f"@{user.username}" if user else "Twitter",
                    snippet=tweet.text[:280],
                    engagement_score=float(min(engagement, 10000)),
                    author=f"@{user.username}" if user else "unknown",
                    verified=is_verified,
                    source_category="eyewitness" if not is_verified else "expert",
                    fetched_at=datetime.utcnow(),
                )
                sources.append(source)

            logger.info(f"Twitter search '{keyword}': {len(sources)} tweets")
            return sources

        except Exception as e:
            logger.warning(f"Twitter search failed '{keyword}': {e}")
            return await self._fallback_search(keyword)

    async def _fallback_trending(self, region: str) -> list[dict]:
        """
        Fallback: Use snscrape or return empty.
        In production, consider using nitter.net instances.
        """
        logger.warning("Twitter trending: No fallback available without API")
        return []

    async def _fallback_search(self, keyword: str) -> list[TopicSource]:
        """Fallback search using nitter or direct scraping."""
        # For now, return empty - in production use snscrape
        logger.warning(f"Twitter search fallback: '{keyword}' skipped")
        return []

    async def get_expert_opinions(
        self, 
        keyword: str, 
        expert_accounts: list[str]
    ) -> list[TopicSource]:
        """
        Search for opinions from specific expert accounts.
        
        expert_accounts: List of Twitter handles to monitor
        (e.g., ["@expert1", "@journalist2"])
        """
        sources = []
        
        for handle in expert_accounts[:10]:  # Limit API calls
            try:
                query = f"from:{handle.lstrip('@')} {keyword}"
                
                tweets = self.client.search_recent_tweets(
                    query=query,
                    max_results=5,
                    tweet_fields=['created_at', 'public_metrics', 'text'],
                )
                
                if tweets.data:
                    for tweet in tweets.data:
                        metrics = tweet.public_metrics
                        engagement = (
                            metrics.get('like_count', 0) +
                            metrics.get('retweet_count', 0) * 2
                        )
                        
                        sources.append(TopicSource(
                            source_type=SourceType.TWITTER,
                            url=f"https://twitter.com/status/{tweet.id}",
                            title=handle,
                            snippet=tweet.text[:280],
                            engagement_score=float(engagement),
                            author=handle,
                            verified=True,
                            source_category="expert",
                            fetched_at=datetime.utcnow(),
                        ))
                        
            except Exception as e:
                logger.debug(f"Expert account {handle} failed: {e}")
                continue

        return sources
