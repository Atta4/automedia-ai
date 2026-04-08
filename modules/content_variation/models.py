"""
Data models for Content Variation Engine.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import hashlib


class VariationProfile(BaseModel):
    """Profile for content variation."""
    
    # Identity
    profile_id: str
    niche: str
    
    # Tone settings
    tone: str  # "energetic", "calm", "authoritative", "conversational"
    formality: float = 0.5  # 0.0 = casual, 1.0 = formal
    energy_level: float = 0.7  # 0.0 = low energy, 1.0 = high energy
    
    # Sentence structure
    avg_sentence_length: str = "medium"  # "short", "medium", "long"
    sentence_variety: float = 0.7  # 0.0 = uniform, 1.0 = varied
    
    # Storytelling
    narrative_style: str = "direct"  # "direct", "story-driven", "analytical"
    perspective: str = "second_person"  # "first_person", "second_person", "third_person"
    
    # Pacing
    pacing: str = "fast"  # "slow", "medium", "fast"
    pause_frequency: float = 0.5  # 0.0 = no pauses, 1.0 = frequent pauses
    
    # Vocabulary
    vocabulary_level: str = "general"  # "simple", "general", "advanced"
    jargon_usage: float = 0.3  # 0.0 = no jargon, 1.0 = heavy jargon
    
    # Humor/Emotion
    humor_level: float = 0.2  # 0.0 = serious, 1.0 = comedic
    emotional_intensity: float = 0.6  # 0.0 = neutral, 1.0 = intense
    
    # Visual style
    visual_intensity: float = 0.7  # 0.0 = minimal, 1.0 = dynamic
    color_temperature: str = "neutral"  # "warm", "neutral", "cool"
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_count: int = 0


class ContentFingerprint(BaseModel):
    """Fingerprint to detect similar content."""
    
    # Hash
    fingerprint: str
    
    # Components
    topic_hash: str
    structure_hash: str
    style_hash: str
    
    # Similarity tracking
    similar_content_ids: List[str] = Field(default_factory=list)
    similarity_score: float = 0.0  # 0.0 = unique, 1.0 = duplicate
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    niche: str
    topic: str


class VariationRequest(BaseModel):
    """Request for content variation."""
    
    niche: str
    topic: str
    existing_content_fingerprints: List[str] = Field(default_factory=list)
    
    # Constraints
    min_uniqueness_score: float = 0.7  # Minimum uniqueness required
    variation_strength: float = 0.5  # How much to vary (0.0-1.0)
    
    # Preferences
    preferred_tones: Optional[List[str]] = None
    excluded_styles: Optional[List[str]] = None


class VariationResult(BaseModel):
    """Result of content variation."""
    
    # Selected profile
    profile: VariationProfile
    
    # Uniqueness metrics
    uniqueness_score: float  # 0.0-1.0
    similarity_to_existing: float  # 0.0-1.0
    
    # Applied variations
    variations_applied: List[str] = Field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class ContentDiversityReport(BaseModel):
    """Report on content diversity across a niche."""
    
    niche: str
    total_content_analyzed: int
    
    # Diversity metrics
    tone_diversity: float  # 0.0-1.0
    style_diversity: float  # 0.0-1.0
    topic_diversity: float  # 0.0-1.0
    
    # Distribution
    tone_distribution: Dict[str, int] = Field(default_factory=dict)
    style_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Recommendations
    underrepresented_tones: List[str] = Field(default_factory=list)
    underrepresented_styles: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class SentencePattern(BaseModel):
    """Pattern for sentence structure variation."""
    
    pattern_type: str  # "simple", "compound", "complex", "fragment"
    structure: str
    example: str
    usage_weight: float  # Probability of selection
