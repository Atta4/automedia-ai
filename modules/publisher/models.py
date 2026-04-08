from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    PENDING   = "pending"     # waiting for human review
    APPROVED  = "approved"    # ready to upload
    REJECTED  = "rejected"    # needs rework or discard
    REWORK    = "rework"      # send back for re-generation


class RejectionReason(str, Enum):
    QUALITY_LOW        = "quality_low"
    FACTUALLY_WRONG    = "factually_wrong"
    POLICY_VIOLATION   = "policy_violation"
    AUDIO_ISSUE        = "audio_issue"
    VISUAL_ISSUE       = "visual_issue"
    TITLE_WEAK         = "title_weak"
    OTHER              = "other"


class ReviewJob(BaseModel):
    """One item in the review queue — links a video to its review state."""

    job_id: str                             # normalized_keyword used as job_id
    topic_keyword: str
    video_path: str
    thumbnail_path: Optional[str] = None
    video_title: str
    video_description: str
    hashtags: list[str] = []
    duration_sec: float = 0.0
    file_size_mb: float = 0.0

    # Review fields
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_note: Optional[str] = None
    rejection_reason: Optional[RejectionReason] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None      # reviewer name/email (optional)

    # Timestamps
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewDecision(BaseModel):
    """Request body for POST /review/{job_id}/approve or /reject."""
    reviewer_note: Optional[str] = None
    reviewed_by: Optional[str] = None


class RejectDecision(BaseModel):
    reason: RejectionReason = RejectionReason.OTHER
    reviewer_note: Optional[str] = None
    reviewed_by: Optional[str] = None


class ReworkDecision(BaseModel):
    instruction: str                        # what to fix (sent back to pipeline)
    reviewed_by: Optional[str] = None
