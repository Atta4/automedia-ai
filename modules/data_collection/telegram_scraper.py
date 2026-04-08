"""
Telegram Channel Scraper for on-ground reports and local news.

Uses Telethon (async Telegram client) to monitor:
- Local news channels
- Citizen journalist reports
- Regional updates
- On-ground footage

Note: Requires Telegram API credentials (free from my.telegram.org)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from core.models import TopicSource, SourceType
from config.settings import get_settings


# Default news/region-specific channels to monitor
# Users should customize based on their focus regions
DEFAULT_CHANNELS = [
    # Pakistan
    "DawnNews",
    "GeoNews",
    "ARYNewsOfficial",
    # Middle East
    "AlJazeera",
    "MiddleEastEye",
    # International
    "Reuters",
    "APNews",
]


class TelegramScraper:
    """
    Collects on-ground reports from Telegram channels.
    
    Advantages:
    - Real-time updates (often faster than mainstream)
    - Local journalist reports
    - On-ground footage/photos
    - Regional perspectives
    
    Limitations:
    - Requires API credentials (my.telegram.org)
    - Some channels may be private
    - Verification challenging (anyone can post)
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Telegram client (Telethon)."""
        try:
            from telethon import TelegramClient
            
            api_id = self.settings.telegram_api_id
            api_hash = self.settings.telegram_api_hash
            
            if not api_id or not api_hash:
                logger.warning(
                    "Telegram API not configured - missing TELEGRAM_API_ID/HASH. "
                    "Get credentials from https://my.telegram.org/apps"
                )
                return None

            self.client = TelegramClient(
                'automedia_session',
                int(api_id),
                api_hash,
                system_version="AutoMedia AI",
            )
            
            logger.info("Telegram client initialized")
            
        except ImportError:
            logger.warning("telethon not installed - Telegram scraping disabled")
            return None
        except Exception as e:
            logger.warning(f"Telegram init failed: {e}")
            return None

    async def connect(self):
        """Connect to Telegram (if not already connected)."""
        if self.client and not self.client.is_connected():
            try:
                await self.client.start()
                logger.info("Telegram client connected")
            except Exception as e:
                logger.warning(f"Telegram connection failed: {e}")
                self.client = None

    async def search_topic(self, keyword: str, hours: int = 24) -> list[TopicSource]:
        """
        Search Telegram channels for mentions of a topic.
        """
        if not self.client:
            return await self._fallback_search(keyword)

        sources = []
        channels = self.settings.get_telegram_channels() or DEFAULT_CHANNELS

        try:
            await self.connect()

            for channel in channels[:10]:  # Limit channels
                try:
                    # Search in channel
                    results = await self.client.get_messages(
                        channel,
                        search=keyword,
                        limit=5,
                    )

                    for msg in results:
                        if not msg.message or len(msg.message) < 20:
                            continue

                        # Check if message is recent
                        if msg.date:
                            hours_old = (datetime.utcnow() - msg.date).total_seconds() / 3600
                            if hours_old > hours * 2:
                                continue

                        # Calculate engagement (views + reactions)
                        views = getattr(msg, 'views', 0) or 0
                        reactions = getattr(msg, 'reactions', [])
                        reaction_count = len(reactions) if isinstance(reactions, list) else 0
                        
                        engagement = views * 0.1 + reaction_count * 10

                        source = TopicSource(
                            source_type=SourceType.TELEGRAM,
                            url=f"https://t.me/{channel}/{msg.id}" if msg.id else "",
                            title=f"[{channel}] {msg.message[:50]}...",
                            snippet=msg.message[:280],
                            engagement_score=float(min(engagement, 5000)),
                            author=channel,
                            verified=False,  # Telegram channels not verified
                            source_category="social",
                            fetched_at=datetime.utcnow(),
                        )
                        sources.append(source)

                except Exception as e:
                    logger.debug(f"Channel {channel} search failed: {e}")
                    continue

            logger.info(f"Telegram search '{keyword}': {len(sources)} posts")
            return sources

        except Exception as e:
            logger.warning(f"Telegram search failed: {e}")
            return await self._fallback_search(keyword)

    async def get_channel_updates(
        self, 
        channels: list[str] = None,
        limit: int = 20
    ) -> list[dict]:
        """
        Get recent posts from monitored channels.
        Extract potential trending topics.
        """
        if not self.client:
            return await self._fallback_trending(limit)

        candidates = []
        channels = channels or DEFAULT_CHANNELS

        try:
            await self.connect()

            for channel in channels[:10]:
                try:
                    messages = await self.client.get_messages(
                        channel,
                        limit=limit,
                    )

                    for msg in messages:
                        if not msg.message or len(msg.message) < 30:
                            continue

                        # Extract potential topic from message
                        # (simple: first sentence or 10 words)
                        text = msg.message.split('\n')[0][:100]
                        
                        views = getattr(msg, 'views', 0) or 0
                        
                        candidates.append({
                            "keyword": text.split()[:6],
                            "title": msg.message[:150],
                            "channel": channel,
                            "url": f"https://t.me/{channel}/{msg.id}",
                            "engagement": views * 0.1,
                            "timestamp": msg.date,
                        })

                except Exception:
                    continue

            # Sort by engagement
            candidates.sort(key=lambda x: x["engagement"], reverse=True)
            logger.info(f"Telegram updates: {len(candidates)} posts from {len(channels)} channels")
            return candidates

        except Exception as e:
            logger.warning(f"Telegram updates failed: {e}")
            return await self._fallback_trending(limit)

    async def _fallback_search(self, keyword: str) -> list[TopicSource]:
        """Fallback without API: return empty."""
        logger.warning(f"Telegram search fallback: '{keyword}' skipped (no API)")
        return []

    async def _fallback_trending(self, limit: int) -> list[dict]:
        """Fallback trending: return empty."""
        logger.warning("Telegram trending: skipped (no API)")
        return []

    async def close(self):
        """Close Telegram connection."""
        if self.client:
            try:
                await self.client.disconnect()
                logger.info("Telegram client disconnected")
            except Exception:
                pass
