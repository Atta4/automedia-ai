"""
Data models for Smart Topic Discovery.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TopicSourcePlatform(str, Enum):
    """Platforms for topic sources."""
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    REDDIT = "reddit"
    GOOGLE_TRENDS = "google_trends"
    NEWS = "news"
    RSS = "rss"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class TopicSource(BaseModel):
    """Represents a single source for a topic."""
    
    platform: TopicSourcePlatform
    url: Optional[str] = None
    title: str
    engagement_score: float = 0.0  # 0-100
    reach: Optional[int] = None  # Estimated reach
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ViralityScore(BaseModel):
    """Virality scoring breakdown."""
    
    overall: float = Field(ge=0, le=100)  # Overall virality score 0-100
    
    # Component scores
    trend_score: float = Field(ge=0, le=100, default=0)  # How trending
    emotional_score: float = Field(ge=0, le=100, default=0)  # Emotional impact
    ctr_potential: float = Field(ge=0, le=100, default=0)  # Click-through potential
    engagement_potential: float = Field(ge=0, le=100, default=0)  # Engagement likelihood
    novelty_score: float = Field(ge=0, le=100, default=0)  # Uniqueness
    
    # Scoring factors
    factors: Dict[str, float] = Field(default_factory=dict)
    reason: str = ""  # Human-readable explanation


class DiscoveredTopic(BaseModel):
    """A discovered topic with virality analysis."""
    
    # Core topic info
    niche: str
    topic: str
    normalized_keyword: str
    
    # Virality assessment
    virality_score: ViralityScore
    
    # Sources
    sources: List[TopicSource] = Field(default_factory=list)
    source_count: int = 0
    
    # Emotional analysis
    emotional_triggers: List[str] = Field(default_factory=list)
    primary_emotion: Optional[str] = None
    
    # CTR optimization
    ctr_patterns: List[str] = Field(default_factory=list)
    hook_potential: float = 0.0  # 0-100
    
    # Metadata
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Validation
    is_validated: bool = False
    validation_reason: str = ""
    
    # Timestamps
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # Topics may expire
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate source count
        if not self.source_count and self.sources:
            self.source_count = len(self.sources)


class TopicDiscoveryResult(BaseModel):
    """Result from topic discovery engine."""
    
    niche: str
    topics: List[DiscoveredTopic]
    total_discovered: int
    total_validated: int
    avg_virality_score: float
    discovery_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Performance metrics
    discovery_duration_sec: Optional[float] = None
    sources_checked: int = 0


class TrendingTopic(BaseModel):
    """Raw trending topic from a source."""
    
    platform: TopicSourcePlatform
    title: str
    keyword: str
    trend_score: float  # Platform-specific trend score
    engagement: Optional[int] = None
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TopicGenerationRequest(BaseModel):
    """Request for topic generation."""
    
    niche: str
    region: str = "US"
    language: str = "en"
    min_virality_score: int = 60
    max_topics: int = 10
    exclude_keywords: List[str] = Field(default_factory=list)
    focus_keywords: Optional[List[str]] = None
    include_trending: bool = True


class TopicCategory(BaseModel):
    """Topic category for classification."""
    
    name: str
    keywords: List[str]
    emotional_profile: List[str]
    typical_virality_range: tuple = (50, 80)
