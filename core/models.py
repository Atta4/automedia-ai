from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ContentStyle(str, Enum):
    JOURNALIST = "journalist"
    COMMENTARY = "commentary"
    HUMOROUS = "humorous"
    ROAST = "roast"


class TopicStatus(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    SCRIPTED = "scripted"
    VOICED = "voiced"
    ASSEMBLED = "assembled"
    REVIEWED = "reviewed"
    UPLOADED = "uploaded"
    FAILED = "failed"


class SourceType(str, Enum):
    GOOGLE_TRENDS = "google_trends"
    NEWS_API = "news_api"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    REDDIT = "reddit"
    RSS_FEED = "rss_feed"
    TELEGRAM = "telegram"


# ── Topic Models ─────────────────────────────────────────────────────────────

class TopicSource(BaseModel):
    source_type: SourceType
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: Optional[str] = None
    engagement_score: float = 0.0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    # Additional metadata for source verification
    author: Optional[str] = None        # Twitter handle, Reddit user, etc.
    verified: bool = False              # Is author verified (Twitter) or trusted
    source_category: Optional[str] = None  # "mainstream" | "independent" | "social" | "eyewitness"


class TrendingTopic(BaseModel):
    keyword: str
    normalized_keyword: str
    sources: list[TopicSource] = []
    source_count: int = 0
    total_engagement: float = 0.0
    is_validated: bool = False
    validation_reason: Optional[str] = None
    youtube_transcripts: list[str] = []
    status: TopicStatus = TopicStatus.DISCOVERED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def validate_topic(self, min_sources: int = 2) -> bool:
        """Mark topic as validated if enough unique sources confirm it."""
        unique_source_types = {s.source_type for s in self.sources}
        if len(unique_source_types) >= min_sources:
            self.is_validated = True
            self.source_count = len(self.sources)
            self.total_engagement = sum(s.engagement_score for s in self.sources)
            self.status = TopicStatus.VALIDATED
            self.validation_reason = f"Confirmed by {len(unique_source_types)} source types"
            return True
        return False


# ── Script Models ─────────────────────────────────────────────────────────────

class ScriptSegment(BaseModel):
    order: int
    label: str                  # hook / context / evidence / analysis / cta
    text: str
    duration_estimate_sec: float = 0.0
    visual_cue: Optional[str] = None   # hint for visual sourcing


class VideoScript(BaseModel):
    topic_keyword: str
    style: ContentStyle
    title: str
    description: str
    hashtags: list[str] = []
    segments: list[ScriptSegment] = []
    full_text: str = ""
    estimated_duration_sec: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Video Models ─────────────────────────────────────────────────────────────

class VideoAsset(BaseModel):
    asset_type: str             # audio | video_clip | image
    local_path: str
    source_url: Optional[str] = None
    duration_sec: Optional[float] = None
    segment_label: Optional[str] = None


class FinalVideo(BaseModel):
    topic_keyword: str
    output_path: str
    thumbnail_path: Optional[str] = None
    duration_sec: float = 0.0
    file_size_mb: float = 0.0
    script: Optional[VideoScript] = None
    status: TopicStatus = TopicStatus.ASSEMBLED
    created_at: datetime = Field(default_factory=datetime.utcnow)
