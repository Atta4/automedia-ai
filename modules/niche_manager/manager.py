"""
Niche Manager - Core orchestration for multi-niche content generation.

Manages niche selection, applies niche-specific strategies, and coordinates
the viral content generation pipeline.
"""

import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from config.niche_config import (
    NicheConfig,
    NicheType,
    ContentTone,
    HookStrategy,
    EmotionalTrigger,
    niche_config_manager,
)


class TopicDiscoveryRequest(BaseModel):
    """Request model for topic discovery."""
    
    niche: str
    region: Optional[str] = "US"
    language: Optional[str] = "en"
    min_virality_score: int = 60
    max_topics: int = 10
    exclude_topics: List[str] = Field(default_factory=list)


class ContentGenerationStrategy(BaseModel):
    """Complete content generation strategy for a niche."""
    
    niche: NicheType
    config: NicheConfig
    
    # Selected strategies for this generation
    selected_tone: ContentTone
    selected_hook: HookStrategy
    primary_emotional_trigger: EmotionalTrigger
    
    # Variation parameters
    variation_seed: int = Field(default_factory=lambda: random.randint(0, 10000))
    creativity_factor: float = 0.7  # 0.0-1.0, higher = more creative
    
    # Generated metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class NicheManager:
    """
    Central manager for multi-niche viral content generation.
    
    Responsibilities:
    - Niche selection and validation
    - Strategy generation for content creation
    - Coordination with topic discovery, script generation, and upload systems
    - Analytics tracking per niche
    """
    
    def __init__(self, db=None):
        """
        Initialize NicheManager.
        
        Args:
            db: MongoDB database connection (optional, for analytics)
        """
        self._config_manager = niche_config_manager
        self._db = db
        self._active_strategies: Dict[str, ContentGenerationStrategy] = {}
    
    def get_available_niches(self) -> List[Dict]:
        """Get all available niches with metadata."""
        return self._config_manager.get_all_niches()
    
    def get_niche_config(self, niche: str) -> Optional[NicheConfig]:
        """
        Get configuration for a specific niche.
        
        Args:
            niche: Niche identifier string
            
        Returns:
            NicheConfig if found, None otherwise
        """
        return self._config_manager.get_niche_by_value(niche)
    
    def validate_niche(self, niche: str) -> bool:
        """Check if a niche is valid and supported."""
        return self._config_manager.get_niche_by_value(niche) is not None
    
    def generate_content_strategy(
        self,
        niche: str,
        topic: Optional[str] = None,
        creativity_factor: Optional[float] = None
    ) -> ContentGenerationStrategy:
        """
        Generate a content generation strategy for a niche.
        
        Args:
            niche: Niche identifier
            topic: Optional topic to influence strategy selection
            creativity_factor: Optional override for creativity (0.0-1.0)
            
        Returns:
            ContentGenerationStrategy with selected parameters
        """
        config = self.get_niche_config(niche)
        if not config:
            raise ValueError(f"Unknown niche: {niche}")
        
        niche_type = NicheType(niche)
        
        # Select tone (random from preferred, or influenced by topic)
        selected_tone = self._select_tone(config, topic)
        
        # Select hook strategy (random from preferred)
        selected_hook = self._select_hook_strategy(config, topic)
        
        # Select primary emotional trigger
        primary_trigger = self._select_emotional_trigger(config, topic)
        
        # Creativity factor
        if creativity_factor is None:
            creativity_factor = config.virality_threshold / 100.0
        
        strategy = ContentGenerationStrategy(
            niche=niche_type,
            config=config,
            selected_tone=selected_tone,
            selected_hook=selected_hook,
            primary_emotional_trigger=primary_trigger,
            variation_seed=random.randint(0, 10000),
            creativity_factor=creativity_factor,
        )
        
        # Cache strategy
        strategy_key = f"{niche}_{strategy.generated_at.timestamp()}"
        self._active_strategies[strategy_key] = strategy
        
        return strategy
    
    def _select_tone(
        self,
        config: NicheConfig,
        topic: Optional[str] = None
    ) -> ContentTone:
        """Select content tone based on niche and optional topic."""
        if not config.default_tones:
            return ContentTone.EDUCATIONAL
        
        # Topic-influenced selection
        if topic:
            topic_lower = topic.lower()
            
            # Urgent topics
            if any(word in topic_lower for word in ["breaking", "urgent", "alert", "now"]):
                return ContentTone.URGENT
            
            # Story topics
            if any(word in topic_lower for word in ["story", "history", "biography"]):
                return ContentTone.DRAMATIC
            
            # Educational topics
            if any(word in topic_lower for word in ["how to", "guide", "tutorial", "explained"]):
                return ContentTone.EDUCATIONAL
        
        # Random selection from preferred tones
        return random.choice(config.default_tones)
    
    def _select_hook_strategy(
        self,
        config: NicheConfig,
        topic: Optional[str] = None
    ) -> HookStrategy:
        """Select hook strategy based on niche and optional topic."""
        if not config.hook_strategies:
            return HookStrategy.PATTERN_INTERRUPT
        
        # Topic-influenced selection
        if topic:
            topic_lower = topic.lower()
            
            # Question-worthy topics
            if topic_lower.startswith("why") or topic_lower.startswith("how"):
                return HookStrategy.THIS_IS_WHY
            
            # List-worthy topics
            if any(word in topic_lower for word in ["top", "best", "worst", "secrets"]):
                return HookStrategy.TOP_SECRETS
            
            # Shocking topics
            if any(word in topic_lower for word in ["shocking", "insane", "crazy"]):
                return HookStrategy.YOU_WONT_BELIEVE
        
        # Random selection from preferred strategies
        return random.choice(config.hook_strategies)
    
    def _select_emotional_trigger(
        self,
        config: NicheConfig,
        topic: Optional[str] = None
    ) -> EmotionalTrigger:
        """Select primary emotional trigger based on niche and topic."""
        if not config.emotional_triggers:
            return EmotionalTrigger.CURIOSITY
        
        # Topic-influenced selection
        if topic:
            topic_lower = topic.lower()
            
            # Fear-based topics
            if any(word in topic_lower for word in ["danger", "warning", "risk", "threat"]):
                return EmotionalTrigger.FEAR
            
            # Inspiration topics
            if any(word in topic_lower for word in ["success", "inspire", "achieve", "overcome"]):
                return EmotionalTrigger.INSPIRATION
            
            # Curiosity topics
            if any(word in topic_lower for word in ["secret", "hidden", "unknown", "mystery"]):
                return EmotionalTrigger.CURIOSITY
            
            # Surprise topics
            if any(word in topic_lower for word in ["unexpected", "shocking", "surprising"]):
                return EmotionalTrigger.SURPRISE
        
        # Random selection from preferred triggers
        return random.choice(config.emotional_triggers)
    
    def get_topic_sources(self, niche: str) -> Dict[str, List[str]]:
        """
        Get recommended topic discovery sources for a niche.
        
        Returns:
            Dict with 'primary' and 'secondary' source lists
        """
        config = self.get_niche_config(niche)
        if not config:
            return {"primary": ["youtube", "twitter"], "secondary": ["reddit"]}
        
        return {
            "primary": config.primary_sources,
            "secondary": config.secondary_sources,
        }
    
    def get_optimal_posting_time(self, niche: str) -> str:
        """
        Get optimal posting time for a niche.
        
        Returns:
            ISO format hour string (e.g., "14:00")
        """
        config = self.get_niche_config(niche)
        if not config or not config.optimal_posting_times:
            return "18:00"  # Default
        
        # Select based on current day/time
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Find closest optimal time
        optimal_times = config.optimal_posting_times
        closest = min(optimal_times, key=lambda t: abs(int(t.split(":")[0]) - current_hour))
        
        return closest
    
    def get_upload_limits(self, niche: str) -> Dict[str, int]:
        """
        Get upload limits for a niche.
        
        Returns:
            Dict with 'daily_limit' and 'priority'
        """
        config = self.get_niche_config(niche)
        if not config:
            return {"daily_limit": 3, "priority": 2}
        
        return {
            "daily_limit": config.daily_upload_limit,
            "priority": config.upload_priority,
        }
    
    def get_script_parameters(self, niche: str) -> Dict[str, Any]:
        """
        Get script generation parameters for a niche.
        
        Returns:
            Dict with duration, pacing, voice, and hook settings
        """
        config = self.get_niche_config(niche)
        if not config:
            return {
                "target_duration_sec": 90,
                "hook_duration_sec": 3,
                "pacing": "medium",
                "preferred_voices": ["alloy"],
                "voice_speed": 1.0,
            }
        
        return {
            "target_duration_sec": config.target_duration_sec,
            "hook_duration_sec": config.hook_duration_sec,
            "pacing": config.pacing,
            "preferred_voices": config.preferred_voices,
            "voice_speed": config.voice_speed,
            "retention_hook_interval_sec": config.retention_hook_interval_sec,
        }
    
    def get_visual_parameters(self, niche: str) -> Dict[str, Any]:
        """
        Get visual generation parameters for a niche.
        
        Returns:
            Dict with style, color palette, and thumbnail settings
        """
        config = self.get_niche_config(niche)
        if not config:
            return {
                "visual_style": "dynamic",
                "color_palette": ["#3B82F6", "#10B981", "#F59E0B"],
                "thumbnail_styles": ["standard"],
            }
        
        return {
            "visual_style": config.visual_style,
            "color_palette": config.color_palette,
            "thumbnail_styles": config.thumbnail_styles,
        }
    
    def get_title_patterns(self, niche: str) -> List[str]:
        """Get title generation patterns for a niche."""
        config = self.get_niche_config(niche)
        if not config:
            return [
                "The Truth About {topic}",
                "Why {topic} Matters",
                "What Nobody Tells You About {topic}"
            ]
        
        return config.title_patterns
    
    def get_cta_style(self, niche: str) -> str:
        """Get recommended CTA style for a niche."""
        config = self.get_niche_config(niche)
        if not config:
            return "subscribe"
        
        return config.cta_style
    
    async def track_niche_analytics(
        self,
        niche: str,
        metric_type: str,
        value: float,
        topic: Optional[str] = None
    ) -> None:
        """
        Track analytics for a niche (if database is available).
        
        Args:
            niche: Niche identifier
            metric_type: Type of metric (views, ctr, watch_time, etc.)
            value: Metric value
            topic: Optional topic identifier
        """
        if not self._db:
            return
        
        try:
            await self._db.niche_analytics.insert_one({
                "niche": niche,
                "metric_type": metric_type,
                "value": value,
                "topic": topic,
                "timestamp": datetime.utcnow(),
            })
        except Exception:
            pass  # Silently fail for analytics
    
    async def get_niche_performance(
        self,
        niche: str,
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics for a niche.
        
        Args:
            niche: Niche identifier
            days: Number of days to analyze
            
        Returns:
            Dict with performance metrics or None if no data
        """
        if not self._db:
            return None
        
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {
                    "$match": {
                        "niche": niche,
                        "timestamp": {"$gte": cutoff}
                    }
                },
                {
                    "$group": {
                        "_id": "$metric_type",
                        "avg_value": {"$avg": "$value"},
                        "total_value": {"$sum": "$value"},
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = await self._db.niche_analytics.aggregate(pipeline).to_list(length=100)
            
            if not results:
                return None
            
            return {
                "niche": niche,
                "period_days": days,
                "metrics": {r["_id"]: r for r in results},
            }
        except Exception:
            return None
