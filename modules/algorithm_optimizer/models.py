"""
Data models for Algorithm Optimization.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TitleVariant(BaseModel):
    """A variant of a video title."""
    
    text: str
    style: str  # "curiosity", "urgent", "question", "list", "shock"
    ctr_score: float = 0.0  # 0-100
    character_count: int = 0
    has_numbers: bool = False
    has_question: bool = False
    has_power_words: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.character_count and self.text:
            self.character_count = len(self.text)
        if not self.has_numbers and self.text:
            self.has_numbers = any(c.isdigit() for c in self.text)
        if not self.has_question and self.text:
            self.has_question = self.text.endswith("?")


class DescriptionSection(BaseModel):
    """A section of the video description."""
    
    type: str  # "hook", "body", "cta", "links", "timestamps", "hashtags"
    content: str
    order: int


class VideoMetadata(BaseModel):
    """Complete optimized video metadata."""
    
    # Titles
    primary_title: str
    title_variants: List[TitleVariant] = Field(default_factory=list)
    best_title: str = ""  # Auto-selected best title
    
    # Description
    description: str
    description_sections: List[DescriptionSection] = Field(default_factory=list)
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    
    # Categorization
    category_id: str = "25"  # YouTube category
    language: str = "en"
    
    # Thumbnail optimization
    thumbnail_text: Optional[str] = None
    thumbnail_style: Optional[str] = None
    
    # Engagement optimization
    pinned_comment: Optional[str] = None
    community_post_text: Optional[str] = None
    
    # Scheduling
    optimal_publish_time: Optional[str] = None
    
    # Scores
    seo_score: float = 0.0
    ctr_score: float = 0.0
    
    # Metadata
    niche: str
    topic: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.best_title and self.primary_title:
            self.best_title = self.primary_title


class SEOScore(BaseModel):
    """SEO quality score breakdown."""
    
    overall: float  # 0-100
    
    # Component scores
    title_score: float = 0.0
    description_score: float = 0.0
    tags_score: float = 0.0
    hashtag_score: float = 0.0
    
    # Analysis
    keyword_density: float = 0.0
    has_timestamps: bool = False
    has_cta: bool = False
    has_links: bool = False
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class CTRAnalysis(BaseModel):
    """Click-through rate analysis."""
    
    # Overall CTR potential
    ctr_potential: float  # 0-100
    
    # Title analysis
    title_length_optimal: bool
    title_has_numbers: bool
    title_has_question: bool
    title_has_power_words: bool
    title_emotional_score: float
    
    # Thumbnail analysis (if applicable)
    thumbnail_text_present: bool
    thumbnail_contrast_score: float
    thumbnail_face_present: bool
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class PlatformOptimization(BaseModel):
    """Platform-specific optimization settings."""
    
    platform: str  # "youtube", "youtube_shorts", "instagram_reels", "tiktok"
    
    # Format settings
    aspect_ratio: str  # "16:9", "9:16", "1:1"
    max_duration_sec: int
    preferred_resolution: str
    
    # Metadata requirements
    title_max_length: int
    description_max_length: int
    max_tags: int
    max_hashtags: int
    
    # Optimization settings
    subtitle_style: str  # "burned_in", "soft", "none"
    hook_duration_sec: int
    cta_placement: str  # "end", "middle", "throughout"


class MetadataGenerationRequest(BaseModel):
    """Request for metadata generation."""
    
    niche: str
    topic: str
    script_title: Optional[str] = None
    script_content: Optional[str] = None
    
    # Platform
    platform: str = "youtube"
    video_format: str = "standard"  # "standard", "shorts"
    
    # Optimization goals
    primary_goal: str = "views"  # "views", "subscribers", "engagement"
    target_audience: Optional[str] = None
    
    # Constraints
    exclude_words: List[str] = Field(default_factory=list)
    required_keywords: List[str] = Field(default_factory=list)


class TitlePattern(BaseModel):
    """A pattern for generating titles."""
    
    pattern: str
    style: str
    effectiveness_by_niche: Dict[str, float] = Field(default_factory=dict)
    example: Optional[str] = None


class KeywordData(BaseModel):
    """Keyword research data."""
    
    keyword: str
    search_volume: int
    competition: str  # "low", "medium", "high"
    relevance_score: float
    trend: str  # "rising", "stable", "declining"
    cpc: Optional[float] = None
