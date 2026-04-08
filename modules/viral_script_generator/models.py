"""
Data models for Viral Script Generator.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class HookFramework(str, Enum):
    """Proven hook frameworks for viral content."""
    
    # Curiosity-based hooks
    YOU_WONT_BELIEVE = "you_wont_believe"  # "You won't believe what happened..."
    THE_TRUTH_ABOUT = "the_truth_about"  # "The truth about X that nobody tells you"
    WHAT_NOBODY_KNOWS = "what_nobody_knows"  # "What nobody knows about X"
    
    # List-based hooks
    TOP_NUMBER = "top_number"  # "Top 3 secrets to..."
    NUMBER_WAYS = "number_ways"  # "5 ways to..."
    NUMBER_MISTAKES = "number_mistakes"  # "7 mistakes you're making..."
    
    # Story-based hooks
    STORY_BASED = "story_based"  # "Let me tell you a story..."
    PERSONAL_EXPERIENCE = "personal_experience"  # "When I first started..."
    CASE_STUDY = "case_study"  # "How X achieved Y..."
    
    # Question-based hooks
    WHY_QUESTION = "why_question"  # "Why does X happen?"
    HOW_QUESTION = "how_question"  # "How can you achieve X?"
    WHAT_IF = "what_if"  # "What if I told you..."
    
    # Shock-based hooks
    PATTERN_INTERRUPT = "pattern_interrupt"  # Unexpected statement
    CONTROVERSIAL = "controversial"  # "X is a lie..."
    URGENT_WARNING = "urgent_warning"  # "Stop doing X immediately!"
    
    # Result-based hooks
    THIS_IS_WHY = "this_is_why"  # "This is why you're not..."
    REASON_X = "reason_x"  # "The #1 reason people fail at..."
    SECRET_TO = "secret_to"  # "The secret to achieving..."


class ScriptSegmentType(str, Enum):
    """Types of script segments."""
    HOOK = "hook"
    OPEN_LOOP = "open_loop"
    CONTEXT = "context"
    CONTENT = "content"
    RETENTION_HOOK = "retention_hook"
    TRANSITION = "transition"
    CLIMAX = "climax"
    CTA = "cta"
    TWIST = "twist"


class ScriptSegment(BaseModel):
    """A segment of the script."""
    
    type: ScriptSegmentType
    order: int
    text: str
    duration_estimate_sec: float
    visual_cue: Optional[str] = None
    emphasis: Optional[str] = None  # "strong", "normal", "whisper"
    on_screen_text: Optional[str] = None  # Text to display on screen
    
    # Retention optimization
    has_pattern_interrupt: bool = False
    has_open_loop: bool = False


class ViralScript(BaseModel):
    """Complete viral-optimized script."""
    
    # Core info
    niche: str
    topic: str
    title: str
    
    # Hook configuration
    hook_framework: HookFramework
    hook_text: str
    
    # Script structure
    segments: List[ScriptSegment]
    full_text: str
    
    # Metadata
    estimated_duration_sec: float
    word_count: int
    
    # Optimization scores
    retention_score: float = 0.0  # 0-100
    pacing_score: float = 0.0  # 0-100
    emotional_arc_score: float = 0.0  # 0-100
    
    # SEO
    description: str
    tags: List[str]
    hashtags: List[str]
    
    # CTA
    cta_text: str
    cta_type: str  # "subscribe", "comment", "like", "share"
    
    # Variation tracking
    variation_seed: int = 0
    creativity_factor: float = 0.7
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate word count and duration if not provided
        if not self.word_count and self.full_text:
            self.word_count = len(self.full_text.split())
        if not self.estimated_duration_sec and self.full_text:
            # Average speaking rate: ~150 words per minute
            self.estimated_duration_sec = (self.word_count / 150) * 60


class ScriptGenerationRequest(BaseModel):
    """Request for script generation."""
    
    niche: str
    topic: str
    topic_keyword: Optional[str] = None
    
    # Strategy
    hook_framework: Optional[HookFramework] = None
    tone: Optional[str] = None
    emotional_trigger: Optional[str] = None
    
    # Parameters
    target_duration_sec: int = 90
    creativity_factor: float = 0.7
    variation_seed: Optional[int] = None
    
    # Reference material
    reference_material: Optional[str] = None
    
    # Constraints
    exclude_topics: List[str] = Field(default_factory=list)
    required_points: List[str] = Field(default_factory=list)


class ScriptQualityMetrics(BaseModel):
    """Quality metrics for a generated script."""
    
    # Scores
    overall_quality: float  # 0-100
    hook_strength: float  # 0-100
    retention_potential: float  # 0-100
    pacing_quality: float  # 0-100
    emotional_impact: float  # 0-100
    clarity_score: float  # 0-100
    
    # Analysis
    word_count: int
    estimated_duration_sec: float
    segment_count: int
    pattern_interrupt_count: int
    open_loop_count: int
    
    # Recommendations
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class RetentionAnalysis(BaseModel):
    """Retention analysis for a script."""
    
    # Overall retention score
    retention_score: float  # 0-100
    
    # Hook analysis (first 3 seconds)
    hook_effectiveness: float  # 0-100
    hook_type: str
    
    # Retention hooks throughout script
    retention_hooks: List[Dict[str, Any]] = Field(default_factory=list)
    retention_hook_interval_sec: float
    
    # Pacing analysis
    avg_sentence_length: float
    pacing_variety: float  # 0-100
    has_pattern_interrupts: bool
    pattern_interrupt_count: int
    
    # Drop-off risk points
    risk_points: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
