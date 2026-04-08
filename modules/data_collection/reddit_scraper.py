"""
Reddit Scraper for in-depth discussions and community fact-checking.

Uses PRAW (Python Reddit API Wrapper) to collect:
- Trending posts in relevant subreddits
- Community sentiment (upvotes/downvotes)
- Expert AMAs and discussions
- Fact-checking threads
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from core.models import TopicSource, SourceType
from config.settings import get_settings


# Subreddits for news and geopolitical discussions
DEFAULT_SUBREDDITS = [
    "worldnews",
    "news",
    "geopolitics",
    "internationalnews",
    "politics",
    "CurrentEvents",
    "Pakistan",
    "india",
    "israel",
    "palestine",
    "MiddleEastPolitics",
    "SouthAsianPolitics",
]


class RedditScraper:
    """
    Collects trending topics and public discussions from Reddit.
    
    Advantages:
    - Community fact-checking in comments
    - Diverse perspectives (global userbase)
    - In-depth analysis threads
    - Upvote system = community validation
    """

    def __init__(self):
        self.settings = get_settings()
        self.reddit = None
        self._init_client()

    def _init_client(self):
        """Initialize Reddit API client (PRAW)."""
        try:
            import praw
            
            # Reddit API credentials (create at https://www.reddit.com/prefs/apps)
            client_id = getattr(self.settings, 'reddit_client_id', None)
            client_secret = getattr(self.settings, 'reddit_client_secret', None)
            user_agent = getattr(self.settings, 'reddit_user_agent', 
                                 "AutoMediaAI/1.0 by automedia")

            if not client_id or not client_secret:
                logger.warning(
                    "Reddit API not configured - missing REDDIT_CLIENT_ID/SECRET. "
                    "Create app at https://www.reddit.com/prefs/apps"
                )
                return None

            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                read_only=True,  # Read-only access
            )
            logger.info("Reddit API client initialized")
            
        except ImportError:
            logger.warning("praw not installed - Reddit scraping disabled")
            return None
        except Exception as e:
            logger.warning(f"Reddit API init failed: {e}")
            return None

    async def get_trending_topics(self, limit: int = 25) -> list[dict]:
        """
        Get trending posts from news/politics subreddits.
        Returns potential topics based on post titles and engagement.
        """
        if not self.reddit:
            return await self._fallback_trending(limit)

        candidates = []
        seen_keywords = set()

        try:
            for subreddit_name in DEFAULT_SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Get hot posts (trending now)
                    for post in subreddit.hot(limit=limit):
                        # Extract potential keywords from title
                        title = post.title
                        
                        # Skip if already processed
                        if title in seen_keywords:
                            continue
                        seen_keywords.add(title)

                        # Calculate engagement score
                        engagement = (
                            post.score * 2 +  # Upvotes
                            post.num_comments * 3 +  # Comments weighted higher
                            post.upvote_ratio * 10  # Community approval
                        )

                        candidates.append({
                            "keyword": self._extract_keyword(title),
                            "title": title,
                            "subreddit": subreddit_name,
                            "engagement": engagement,
                            "url": f"https://reddit.com{post.permalink}",
                            "score": post.score,
                            "comments": post.num_comments,
                            "ratio": post.upvote_ratio,
                        })

                except Exception as e:
                    logger.debug(f"Subreddit {subreddit_name} failed: {e}")
                    continue

            # Sort by engagement
            candidates.sort(key=lambda x: x["engagement"], reverse=True)
            logger.info(f"Reddit trending: {len(candidates)} posts from {len(DEFAULT_SUBREDDITS)} subreddits")
            
        except Exception as e:
            logger.error(f"Reddit trending failed: {e}")
            return await self._fallback_trending(limit)

        return candidates[:limit * 2]  # Return more for filtering

    async def search_topic(self, keyword: str, hours: int = 24) -> list[TopicSource]:
        """
        Search Reddit for discussions about a specific topic.
        Returns multiple sources from different subreddits.
        """
        if not self.reddit:
            return await self._fallback_search(keyword)

        sources = []

        try:
            # Search across all subreddits
            search_query = f"{keyword} flair:News OR flair:Breaking OR flair:Discussion"
            
            all_reddit = self.reddit.subreddit("all")
            submissions = all_reddit.search(
                search_query,
                sort="relevance",
                time_filter="day",  # Last 24 hours
                limit=20,
            )

            for post in submissions:
                # Skip low-engagement or controversial posts
                if post.score < 10 or post.upvote_ratio < 0.6:
                    continue

                engagement = (
                    post.score * 2 +
                    post.num_comments * 3 +
                    post.upvote_ratio * 20
                )

                source = TopicSource(
                    source_type=SourceType.REDDIT,
                    url=f"https://reddit.com{post.permalink}",
                    title=post.title[:200],
                    snippet=post.selftext[:280] if post.selftext else f"r/{post.subreddit}",
                    engagement_score=float(min(engagement, 15000)),
                    author=f"u/{post.author.name}" if post.author else "anonymous",
                    verified=False,  # Reddit doesn't have verification
                    source_category="community",
                    fetched_at=datetime.utcnow(),
                )
                sources.append(source)

            # Also search specific relevant subreddits for depth
            for subreddit_name in ["worldnews", "geopolitics", "internationalnews"]:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    posts = subreddit.search(keyword, sort="top", time_filter="day", limit=5)
                    
                    for post in posts:
                        if post.score > 50:  # Higher threshold for niche subs
                            engagement = post.score * 3 + post.num_comments * 5
                            
                            sources.append(TopicSource(
                                source_type=SourceType.REDDIT,
                                url=f"https://reddit.com{post.permalink}",
                                title=f"[{subreddit_name}] {post.title[:150]}",
                                snippet=post.selftext[:280] if post.selftext else "",
                                engagement_score=float(min(engagement, 20000)),
                                author=f"u/{post.author.name}" if post.author else "anonymous",
                                verified=False,
                                source_category="community",
                                fetched_at=datetime.utcnow(),
                            ))
                except Exception:
                    continue

            logger.info(f"Reddit search '{keyword}': {len(sources)} discussions")
            return sources

        except Exception as e:
            logger.warning(f"Reddit search failed '{keyword}': {e}")
            return await self._fallback_search(keyword)

    async def get_top_discussions(
        self, 
        keyword: str, 
        min_comments: int = 50
    ) -> list[TopicSource]:
        """
        Get in-depth discussion threads with high comment counts.
        These often contain expert analysis and fact-checking.
        """
        if not self.reddit:
            return []

        sources = []

        try:
            all_reddit = self.reddit.subreddit("all")
            submissions = all_reddit.search(
                keyword,
                sort="top",
                time_filter="week",
                limit=30,
            )

            for post in submissions:
                if post.num_comments >= min_comments:
                    # High-comment threads = detailed discussions
                    engagement = post.score * 2 + post.num_comments * 10
                    
                    sources.append(TopicSource(
                        source_type=SourceType.REDDIT,
                        url=f"https://reddit.com{post.permalink}",
                        title=f"[{post.subreddit}] {post.title[:150]}",
                        snippet=f"{post.num_comments} comments discussing {keyword}",
                        engagement_score=float(min(engagement, 25000)),
                        author=f"u/{post.author.name}" if post.author else "anonymous",
                        verified=False,
                        source_category="community",
                        fetched_at=datetime.utcnow(),
                    ))

            logger.info(f"Reddit top discussions '{keyword}': {len(sources)} threads")
            return sources

        except Exception as e:
            logger.warning(f"Reddit top discussions failed: {e}")
            return []

    def _extract_keyword(self, title: str) -> str:
        """Extract main keyword from Reddit post title."""
        # Remove common prefixes
        prefixes = [
            "BREAKING:", "Breaking:", "UPDATE:", "Update:",
            "[News]", "[Discussion]", "[Analysis]",
        ]
        for prefix in prefixes:
            title = title.replace(prefix, "").strip()
        
        # Return first 5-7 words as keyword
        words = title.split()[:6]
        return " ".join(words)

    async def _fallback_trending(self, limit: int) -> list[dict]:
        """Fallback without API: use pushshift.io or return empty."""
        logger.warning("Reddit trending: No fallback without API credentials")
        return []

    async def _fallback_search(self, keyword: str) -> list[TopicSource]:
        """Fallback search using pushshift.io API."""
        try:
            # Pushshift API (free, no auth needed)
            import httpx
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.pushshift.io/reddit/search/submission/",
                    params={
                        "q": keyword,
                        "size": 20,
                        "sort": "score",
                        "time_filter": "day",
                    }
                )
                data = response.json()

            sources = []
            for post in data.get("data", [])[:10]:
                score = post.get("score", 0)
                comments = post.get("num_comments", 0)
                
                sources.append(TopicSource(
                    source_type=SourceType.REDDIT,
                    url=f"https://reddit.com/r/{post.get('subreddit')}/comments/{post.get('id')}",
                    title=post.get("title", "")[:200],
                    snippet=post.get("selftext", "")[:280],
                    engagement_score=float(score * 2 + comments * 3),
                    author=post.get("author", "anonymous"),
                    verified=False,
                    source_category="community",
                    fetched_at=datetime.utcnow(),
                ))
            
            return sources

        except Exception as e:
            logger.warning(f"Reddit pushshift fallback failed: {e}")
            return []
