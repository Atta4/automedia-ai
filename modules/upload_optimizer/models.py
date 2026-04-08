"""
Data models for Upload Strategy Optimizer.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class UploadStatus(str, Enum):
    """Status of an upload job."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    RATE_LIMITED = "rate_limited"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class UploadPriority(str, Enum):
    """Priority levels for upload jobs."""
    CRITICAL = "critical"  # Breaking news
    HIGH = "high"  # Trending topics
    NORMAL = "normal"  # Regular content
    LOW = "low"  # Evergreen content


class UploadJob(BaseModel):
    """Represents a video upload job."""
    
    # Identity
    job_id: str
    video_id: Optional[str] = None  # MongoDB video ID
    
    # Content info
    niche: str
    topic: str
    title: str
    
    # Files
    video_path: str
    thumbnail_path: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Scheduling
    priority: UploadPriority = UploadPriority.NORMAL
    scheduled_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    status: UploadStatus = UploadStatus.PENDING
    status_message: Optional[str] = None
    
    # Retry handling
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None
    
    # YouTube API response
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    upload_response: Optional[Dict[str, Any]] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-set scheduled time if not provided
        if not self.scheduled_time and self.status == UploadStatus.SCHEDULED:
            self.scheduled_time = datetime.utcnow() + timedelta(hours=1)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    
    # Daily limits
    daily_upload_limit: int = 10
    daily_uploads_count: int = 0
    daily_reset_time: str = "00:00"  # UTC
    
    # Hourly limits
    hourly_upload_limit: int = 3
    hourly_uploads_count: int = 0
    
    # API quota
    api_quota_limit: int = 10000  # YouTube API units
    api_quota_used: int = 0
    api_quota_reset_date: Optional[str] = None
    
    # Cooldown settings
    upload_cooldown_sec: int = 300  # 5 minutes between uploads
    last_upload_time: Optional[datetime] = None
    
    # Error handling
    consecutive_errors: int = 0
    max_consecutive_errors: int = 5
    error_cooldown_sec: int = 3600  # 1 hour after max errors
    
    def can_upload(self) -> tuple:
        """
        Check if upload is allowed under rate limits.
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        now = datetime.utcnow()
        
        # Check daily limit
        if self.daily_uploads_count >= self.daily_upload_limit:
            return False, "Daily upload limit reached"
        
        # Check hourly limit
        if self.hourly_uploads_count >= self.hourly_upload_limit:
            return False, "Hourly upload limit reached"
        
        # Check cooldown
        if self.last_upload_time:
            elapsed = (now - self.last_upload_time).total_seconds()
            if elapsed < self.upload_cooldown_sec:
                remaining = self.upload_cooldown_sec - elapsed
                return False, f"Upload cooldown active ({remaining:.0f}s remaining)"
        
        # Check error cooldown
        if self.consecutive_errors >= self.max_consecutive_errors:
            return False, "Too many consecutive errors - cooldown active"
        
        return True, "OK"
    
    def record_upload(self) -> None:
        """Record a successful upload."""
        self.daily_uploads_count += 1
        self.hourly_uploads_count += 1
        self.last_upload_time = datetime.utcnow()
        self.consecutive_errors = 0
    
    def record_error(self, error_type: str) -> None:
        """Record an upload error."""
        self.consecutive_errors += 1
        
        # Special handling for rate limit errors
        if "rateLimit" in error_type or "quota" in error_type.lower():
            self.consecutive_errors = self.max_consecutive_errors


class UploadStrategy(BaseModel):
    """Upload strategy configuration."""
    
    # Strategy name
    name: str
    
    # Timing
    optimal_times: List[str] = Field(default_factory=list)  # ISO format hours
    timezone: str = "UTC"
    
    # Frequency
    uploads_per_day: int = 5
    min_interval_minutes: int = 30
    
    # Priority rules
    priority_niches: List[str] = Field(default_factory=list)
    boost_trending: bool = True
    
    # Scheduling
    schedule_uploads: bool = True
    schedule_ahead_hours: int = 24
    
    # Platform-specific
    make_public_immediately: bool = True
    schedule_premiere: bool = False
    
    # Retry configuration
    auto_retry: bool = True
    max_retries: int = 3
    retry_delay_base_sec: int = 300  # 5 minutes
    retry_delay_multiplier: float = 2.0  # Exponential backoff
    
    def get_retry_delay(self, retry_count: int) -> int:
        """Calculate retry delay with exponential backoff."""
        delay = self.retry_delay_base_sec * (self.retry_delay_multiplier ** retry_count)
        return int(min(delay, 86400))  # Cap at 24 hours


class UploadQueueStatus(BaseModel):
    """Status of the upload queue."""
    
    # Queue counts
    total_jobs: int
    pending_jobs: int
    processing_jobs: int
    scheduled_jobs: int
    failed_jobs: int
    
    # Rate limit status
    can_upload: bool
    rate_limit_reason: str
    next_available_slot: Optional[datetime] = None
    
    # Today's stats
    uploads_today: int
    daily_limit: int
    remaining_today: int
    
    # Performance
    avg_upload_time_sec: float
    success_rate: float


class UploadAnalytics(BaseModel):
    """Analytics for upload performance."""
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Counts
    total_uploads: int
    successful_uploads: int
    failed_uploads: int
    
    # Timing
    avg_upload_duration_sec: float
    fastest_upload_sec: float
    slowest_upload_sec: float
    
    # By niche
    uploads_by_niche: Dict[str, int] = Field(default_factory=dict)
    success_by_niche: Dict[str, float] = Field(default_factory=dict)
    
    # By time
    uploads_by_hour: Dict[int, int] = Field(default_factory=dict)
    best_performing_hour: Optional[int] = None
    
    # Errors
    error_distribution: Dict[str, int] = Field(default_factory=dict)
    most_common_error: Optional[str] = None


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    
    # Enable/disable
    enabled: bool = True
    
    # Retry limits
    max_retries: int = 3
    
    # Delay configuration
    initial_delay_sec: int = 300  # 5 minutes
    max_delay_sec: int = 86400  # 24 hours
    delay_multiplier: float = 2.0
    
    # Error-specific handling
    retry_on_quota_exceeded: bool = True
    quota_retry_delay_sec: int = 86400  # 24 hours
    
    retry_on_upload_limit: bool = True
    upload_limit_retry_delay_sec: int = 86400  # 24 hours
    
    retry_on_network_error: bool = True
    network_retry_delay_sec: int = 60  # 1 minute
    
    # Non-retryable errors
    non_retryable_errors: List[str] = Field(default_factory=lambda: [
        "invalid_credentials",
        "file_not_found",
        "invalid_format",
        "account_suspended",
    ])
    
    def should_retry(self, error: str) -> bool:
        """Check if an error should be retried."""
        if not self.enabled:
            return False
        
        error_lower = error.lower()
        
        # Check non-retryable errors
        if any(nr in error_lower for nr in self.non_retryable_errors):
            return False
        
        return True
    
    def get_delay_for_error(self, error: str, retry_count: int) -> int:
        """Get appropriate delay for an error type."""
        error_lower = error.lower()
        
        if "quota" in error_lower:
            return self.quota_retry_delay_sec
        
        if "uploadlimit" in error_lower or "daily limit" in error_lower:
            return self.upload_limit_retry_delay_sec
        
        if "network" in error_lower or "connection" in error_lower:
            return self.network_retry_delay_sec
        
        # Exponential backoff for other errors
        delay = self.initial_delay_sec * (self.delay_multiplier ** retry_count)
        return int(min(delay, self.max_delay_sec))
