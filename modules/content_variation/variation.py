"""
Content Variation Engine

Ensures each piece of content feels unique through systematic variation.
"""

import hashlib
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

from .models import (
    VariationProfile,
    ContentFingerprint,
    VariationRequest,
    VariationResult,
    ContentDiversityReport,
    SentencePattern,
)


class ContentVariationEngine:
    """
    Content variation engine for diversity.
    
    Features:
    - Tone randomization
    - Sentence structure variation
    - Storytelling style diversity
    - Content fingerprinting for uniqueness detection
    """
    
    # Available tones
    TONES = [
        "energetic", "calm", "authoritative", "conversational",
        "dramatic", "humorous", "serious", "inspirational",
    ]
    
    # Narrative styles
    NARRATIVE_STYLES = [
        "direct", "story-driven", "analytical", "question-based",
        "problem-solution", "chronological", "comparison",
    ]
    
    # Perspectives
    PERSPECTIVES = ["first_person", "second_person", "third_person"]
    
    # Sentence patterns
    SENTENCE_PATTERNS = [
        SentencePattern(
            pattern_type="simple",
            structure="Subject + Verb + Object",
            example="This changes everything.",
            usage_weight=0.3,
        ),
        SentencePattern(
            pattern_type="compound",
            structure="Independent Clause + Conjunction + Independent Clause",
            example="This is important, and you need to know why.",
            usage_weight=0.25,
        ),
        SentencePattern(
            pattern_type="complex",
            structure="Dependent Clause + Independent Clause",
            example="When you understand this, everything changes.",
            usage_weight=0.25,
        ),
        SentencePattern(
            pattern_type="fragment",
            structure="Incomplete sentence for emphasis",
            example="Mind-blowing.",
            usage_weight=0.2,
        ),
    ]
    
    # Pre-defined variation profiles for diversity
    PRESET_PROFILES = [
        {
            "name": "high_energy_direct",
            "tone": "energetic",
            "formality": 0.3,
            "energy_level": 0.9,
            "avg_sentence_length": "short",
            "narrative_style": "direct",
            "perspective": "second_person",
            "pacing": "fast",
        },
        {
            "name": "calm_authoritative",
            "tone": "authoritative",
            "formality": 0.7,
            "energy_level": 0.4,
            "avg_sentence_length": "medium",
            "narrative_style": "analytical",
            "perspective": "third_person",
            "pacing": "medium",
        },
        {
            "name": "conversational_storyteller",
            "tone": "conversational",
            "formality": 0.2,
            "energy_level": 0.6,
            "avg_sentence_length": "medium",
            "narrative_style": "story-driven",
            "perspective": "first_person",
            "pacing": "medium",
        },
        {
            "name": "dramatic_intense",
            "tone": "dramatic",
            "formality": 0.5,
            "energy_level": 0.8,
            "avg_sentence_length": "varied",
            "narrative_style": "chronological",
            "perspective": "third_person",
            "pacing": "fast",
        },
        {
            "name": "humorous_casual",
            "tone": "humorous",
            "formality": 0.1,
            "energy_level": 0.7,
            "avg_sentence_length": "short",
            "narrative_style": "direct",
            "perspective": "first_person",
            "pacing": "fast",
        },
        {
            "name": "inspirational_coach",
            "tone": "inspirational",
            "formality": 0.4,
            "energy_level": 0.85,
            "avg_sentence_length": "medium",
            "narrative_style": "problem-solution",
            "perspective": "second_person",
            "pacing": "medium",
        },
    ]
    
    def __init__(self, db=None):
        """
        Initialize the variation engine.
        
        Args:
            db: MongoDB database connection for tracking diversity
        """
        self._db = db
        self._profile_history: Dict[str, List[str]] = {}  # niche -> used profile IDs
        self._content_fingerprints: Dict[str, ContentFingerprint] = {}
    
    def generate_variation_profile(
        self,
        request: VariationRequest
    ) -> VariationResult:
        """
        Generate a variation profile for unique content.
        
        Args:
            request: Variation request
            
        Returns:
            VariationResult with profile and uniqueness metrics
        """
        # Select or generate profile
        profile = self._select_profile(
            niche=request.niche,
            existing_fingerprints=request.existing_content_fingerprints,
            preferred_tones=request.preferred_tones,
            excluded_styles=request.excluded_styles,
        )
        
        # Calculate uniqueness
        fingerprint = self._generate_fingerprint(
            niche=request.niche,
            topic=request.topic,
            profile=profile,
        )
        
        # Check similarity to existing content
        similarity = self._calculate_similarity(
            fingerprint=fingerprint,
            existing_fingerprints=request.existing_content_fingerprints,
        )
        
        # Ensure minimum uniqueness
        if similarity > request.min_uniqueness_score:
            # Regenerate with more variation
            profile = self._regenerate_for_uniqueness(
                profile=profile,
                similarity=similarity,
                variation_strength=request.variation_strength,
            )
            
            # Recalculate fingerprint
            fingerprint = self._generate_fingerprint(
                niche=request.niche,
                topic=request.topic,
                profile=profile,
            )
            similarity = self._calculate_similarity(
                fingerprint=fingerprint,
                existing_fingerprints=request.existing_content_fingerprints,
            )
        
        # Generate variations applied list
        variations_applied = self._get_variations_applied(profile)
        
        # Generate recommendations
        recommendations = self._generate_variation_recommendations(profile, similarity)
        
        # Track profile usage
        self._track_profile_usage(request.niche, profile.profile_id)
        
        return VariationResult(
            profile=profile,
            uniqueness_score=1.0 - similarity,
            similarity_to_existing=similarity,
            variations_applied=variations_applied,
            recommendations=recommendations,
        )
    
    def _select_profile(
        self,
        niche: str,
        existing_fingerprints: List[str],
        preferred_tones: Optional[List[str]],
        excluded_styles: Optional[List[str]]
    ) -> VariationProfile:
        """Select or generate a variation profile."""
        # Check if we have preferred tones
        if preferred_tones:
            tone = random.choice(preferred_tones)
        else:
            tone = random.choice(self.TONES)
        
        # Select narrative style (avoid excluded)
        available_styles = [
            s for s in self.NARRATIVE_STYLES
            if not excluded_styles or s not in excluded_styles
        ]
        narrative_style = random.choice(available_styles) if available_styles else "direct"
        
        # Generate profile ID
        profile_id = hashlib.md5(
            f"{niche}_{tone}_{narrative_style}_{datetime.utcnow().timestamp()}".encode()
        ).hexdigest()[:12]
        
        # Create profile with some randomization
        profile = VariationProfile(
            profile_id=profile_id,
            niche=niche,
            tone=tone,
            formality=random.uniform(0.2, 0.8),
            energy_level=random.uniform(0.5, 0.9),
            avg_sentence_length=random.choice(["short", "medium", "long"]),
            sentence_variety=random.uniform(0.5, 0.9),
            narrative_style=narrative_style,
            perspective=random.choice(self.PERSPECTIVES),
            pacing=random.choice(["slow", "medium", "fast"]),
            pause_frequency=random.uniform(0.3, 0.7),
            vocabulary_level=random.choice(["simple", "general", "advanced"]),
            jargon_usage=random.uniform(0.1, 0.5),
            humor_level=random.uniform(0.0, 0.4),
            emotional_intensity=random.uniform(0.4, 0.8),
            visual_intensity=random.uniform(0.5, 0.9),
            color_temperature=random.choice(["warm", "neutral", "cool"]),
        )
        
        return profile
    
    def _generate_fingerprint(
        self,
        niche: str,
        topic: str,
        profile: VariationProfile
    ) -> ContentFingerprint:
        """Generate a content fingerprint."""
        # Topic hash
        topic_hash = hashlib.md5(topic.encode()).hexdigest()[:16]
        
        # Structure hash (based on profile)
        structure_data = f"{profile.narrative_style}_{profile.perspective}_{profile.pacing}"
        structure_hash = hashlib.md5(structure_data.encode()).hexdigest()[:16]
        
        # Style hash (based on tone and other factors)
        style_data = f"{profile.tone}_{profile.energy_level}_{profile.formality}"
        style_hash = hashlib.md5(style_data.encode()).hexdigest()[:16]
        
        # Combined fingerprint
        combined = f"{topic_hash}_{structure_hash}_{style_hash}"
        fingerprint = hashlib.md5(combined.encode()).hexdigest()
        
        return ContentFingerprint(
            fingerprint=fingerprint,
            topic_hash=topic_hash,
            structure_hash=structure_hash,
            style_hash=style_hash,
            niche=niche,
            topic=topic,
        )
    
    def _calculate_similarity(
        self,
        fingerprint: ContentFingerprint,
        existing_fingerprints: List[str]
    ) -> float:
        """Calculate similarity to existing content."""
        if not existing_fingerprints:
            return 0.0
        
        # Simple hash comparison (in production, use more sophisticated similarity)
        matches = sum(1 for fp in existing_fingerprints if fp == fingerprint.fingerprint)
        
        if matches > 0:
            return 1.0  # Exact duplicate
        
        # Partial similarity based on topic hash
        topic_matches = sum(
            1 for fp in existing_fingerprints
            if fp[:16] == fingerprint.topic_hash
        )
        
        # Return normalized similarity
        return min(1.0, topic_matches * 0.3)
    
    def _regenerate_for_uniqueness(
        self,
        profile: VariationProfile,
        similarity: float,
        variation_strength: float
    ) -> VariationProfile:
        """Regenerate profile for better uniqueness."""
        # Determine how much to change
        change_factor = min(1.0, similarity + variation_strength)
        
        # Randomly change attributes based on change factor
        new_profile = profile.model_dump()
        
        if random.random() < change_factor:
            new_profile["tone"] = random.choice(self.TONES)
        
        if random.random() < change_factor:
            new_profile["narrative_style"] = random.choice(self.NARRATIVE_STYLES)
        
        if random.random() < change_factor:
            new_profile["perspective"] = random.choice(self.PERSPECTIVES)
        
        if random.random() < change_factor:
            new_profile["pacing"] = random.choice(["slow", "medium", "fast"])
        
        if random.random() < change_factor:
            new_profile["energy_level"] = random.uniform(0.3, 0.9)
        
        # Generate new profile ID
        new_profile["profile_id"] = hashlib.md5(
            f"{new_profile['niche']}_{new_profile['tone']}_{datetime.utcnow().timestamp()}".encode()
        ).hexdigest()[:12]
        
        return VariationProfile(**new_profile)
    
    def _get_variations_applied(self, profile: VariationProfile) -> List[str]:
        """Get list of variations applied to this profile."""
        variations = []
        
        variations.append(f"tone:{profile.tone}")
        variations.append(f"narrative:{profile.narrative_style}")
        variations.append(f"perspective:{profile.perspective}")
        variations.append(f"pacing:{profile.pacing}")
        variations.append(f"energy:{profile.energy_level:.2f}")
        
        return variations
    
    def _generate_variation_recommendations(
        self,
        profile: VariationProfile,
        similarity: float
    ) -> List[str]:
        """Generate recommendations for variation."""
        recommendations = []
        
        if similarity > 0.5:
            recommendations.append("Consider significantly different tone for next content")
        
        if profile.energy_level > 0.8:
            recommendations.append("High energy content - consider calmer follow-up")
        elif profile.energy_level < 0.4:
            recommendations.append("Low energy content - consider more energetic follow-up")
        
        if profile.narrative_style == "direct":
            recommendations.append("Try story-driven or analytical style next")
        
        if profile.perspective == "second_person":
            recommendations.append("Consider first or third person for variety")
        
        return recommendations
    
    def _track_profile_usage(self, niche: str, profile_id: str) -> None:
        """Track profile usage for diversity analysis."""
        if niche not in self._profile_history:
            self._profile_history[niche] = []
        
        self._profile_history[niche].append(profile_id)
        
        # Keep only last 100
        if len(self._profile_history[niche]) > 100:
            self._profile_history[niche] = self._profile_history[niche][-100:]
    
    def get_diversity_report(self, niche: str) -> ContentDiversityReport:
        """Generate diversity report for a niche."""
        # Get profile history for niche
        profile_ids = self._profile_history.get(niche, [])
        
        if not profile_ids:
            return ContentDiversityReport(
                niche=niche,
                total_content_analyzed=0,
                tone_diversity=0.0,
                style_diversity=0.0,
                topic_diversity=0.0,
            )
        
        # Analyze tone distribution
        tone_counts: Dict[str, int] = {}
        style_counts: Dict[str, int] = {}
        
        # This is simplified - in production, would retrieve full profiles
        for profile_id in profile_ids:
            # Use hash to deterministically assign tone/style for demo
            tone_idx = hash(profile_id) % len(self.TONES)
            style_idx = hash(profile_id) % len(self.NARRATIVE_STYLES)
            
            tone = self.TONES[tone_idx]
            style = self.NARRATIVE_STYLES[style_idx]
            
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
            style_counts[style] = style_counts.get(style, 0) + 1
        
        # Calculate diversity scores (entropy-based)
        tone_diversity = self._calculate_diversity_score(tone_counts)
        style_diversity = self._calculate_diversity_score(style_counts)
        
        # Find underrepresented items
        min_count = min(tone_counts.values()) if tone_counts else 0
        underrepresented_tones = [
            tone for tone, count in tone_counts.items() if count == min_count
        ]
        
        min_style_count = min(style_counts.values()) if style_counts else 0
        underrepresented_styles = [
            style for style, count in style_counts.items() if count == min_style_count
        ]
        
        # Generate recommendations
        recommendations = []
        if tone_diversity < 0.5:
            recommendations.append("Increase tone variety across content")
        if style_diversity < 0.5:
            recommendations.append("Use more diverse narrative styles")
        if underrepresented_tones:
            recommendations.append(f"Consider using more: {', '.join(underrepresented_tones[:2])}")
        
        return ContentDiversityReport(
            niche=niche,
            total_content_analyzed=len(profile_ids),
            tone_diversity=tone_diversity,
            style_diversity=style_diversity,
            topic_diversity=0.7,  # Simplified
            tone_distribution=tone_counts,
            style_distribution=style_counts,
            underrepresented_tones=underrepresented_tones,
            underrepresented_styles=underrepresented_styles,
            recommendations=recommendations,
        )
    
    def _calculate_diversity_score(self, counts: Dict[str, int]) -> float:
        """Calculate diversity score using entropy."""
        if not counts:
            return 0.0
        
        total = sum(counts.values())
        if total == 0:
            return 0.0
        
        # Calculate entropy
        import math
        entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        # Normalize by max entropy
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
        
        return min(1.0, entropy / max_entropy) if max_entropy > 0 else 0.0
    
    def vary_sentence_structure(
        self,
        text: str,
        profile: VariationProfile
    ) -> str:
        """
        Vary sentence structure based on profile.
        
        In production, this would use AI to rewrite sentences.
        """
        # For now, return original text
        # In production, would use LLM to vary structure
        return text
    
    def get_profile_for_tone(self, tone: str, niche: str) -> VariationProfile:
        """Get a profile configured for a specific tone."""
        profile_id = hashlib.md5(
            f"{niche}_{tone}_{datetime.utcnow().timestamp()}".encode()
        ).hexdigest()[:12]
        
        # Configure based on tone
        tone_configs = {
            "energetic": {"energy_level": 0.9, "pacing": "fast", "avg_sentence_length": "short"},
            "calm": {"energy_level": 0.3, "pacing": "slow", "avg_sentence_length": "medium"},
            "authoritative": {"formality": 0.8, "energy_level": 0.5, "narrative_style": "analytical"},
            "conversational": {"formality": 0.2, "energy_level": 0.6, "perspective": "first_person"},
            "dramatic": {"energy_level": 0.8, "emotional_intensity": 0.9, "pacing": "varied"},
            "humorous": {"humor_level": 0.8, "formality": 0.1, "pacing": "fast"},
            "serious": {"humor_level": 0.0, "formality": 0.7, "tone": "authoritative"},
            "inspirational": {"energy_level": 0.85, "emotional_intensity": 0.8, "tone": "energetic"},
        }
        
        config = tone_configs.get(tone, {})
        
        return VariationProfile(
            profile_id=profile_id,
            niche=niche,
            tone=tone,
            **config  # type: ignore
        )
