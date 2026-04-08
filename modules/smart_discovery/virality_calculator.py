"""
Virality Calculator

Calculates virality scores based on multiple factors:
- Trend momentum
- Emotional triggers
- CTR patterns
- Engagement potential
- Novelty/uniqueness
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import ViralityScore, DiscoveredTopic, TopicSource


class ViralityCalculator:
    """
    Calculates virality scores for topics.
    
    Uses a weighted scoring system based on:
    - Trend score (25%): How trending the topic is
    - Emotional score (25%): Emotional impact potential
    - CTR potential (20%): Click-through rate potential
    - Engagement potential (20%): Likelihood of comments/shares
    - Novelty score (10%): Uniqueness/freshness
    """
    
    # Emotional trigger weights
    EMOTIONAL_WEIGHTS = {
        "curiosity": 0.85,
        "surprise": 0.90,
        "shock": 0.95,
        "fear": 0.80,
        "inspiration": 0.75,
        "anger": 0.85,
        "joy": 0.70,
        "urgency": 0.90,
        "controversy": 0.88,
    }
    
    # CTR pattern bonuses
    CTR_PATTERNS = {
        r"\b(you won't believe|unbelievable|insane)\b": 15,
        r"\b(this is why|that's why)\b": 10,
        r"\b(top \d+|best \d+|worst \d+)\b": 12,
        r"\b(secrets|hidden truth|nobody tells)\b": 14,
        r"\b(shocking|shocked|mind-blowing)\b": 13,
        r"\b(breaking|urgent|alert)\b": 11,
        r"\b(what happened|what really)\b": 10,
        r"\b(never|always|every)\b": 8,
        r"\b(\?|why|how|what|when)\b": 7,
        r"\b(\d+)\b": 5,  # Numbers in title
    }
    
    # Weights for final score calculation
    SCORE_WEIGHTS = {
        "trend": 0.25,
        "emotional": 0.25,
        "ctr": 0.20,
        "engagement": 0.20,
        "novelty": 0.10,
    }
    
    def __init__(self):
        self._compiled_ctr_patterns = [
            (re.compile(pattern, re.IGNORECASE), bonus)
            for pattern, bonus in self.CTR_PATTERNS.items()
        ]
    
    def calculate(
        self,
        topic: str,
        sources: List[TopicSource],
        emotional_triggers: Optional[List[str]] = None,
        niche: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ViralityScore:
        """
        Calculate virality score for a topic.
        
        Args:
            topic: Topic title/text
            sources: List of topic sources
            emotional_triggers: Detected emotional triggers
            niche: Optional niche for niche-specific scoring
            metadata: Additional metadata for scoring
            
        Returns:
            ViralityScore with breakdown
        """
        # Calculate component scores
        trend_score = self._calculate_trend_score(sources)
        emotional_score = self._calculate_emotional_score(topic, emotional_triggers or [])
        ctr_potential = self._calculate_ctr_potential(topic)
        engagement_potential = self._calculate_engagement_potential(sources, topic)
        novelty_score = self._calculate_novelty_score(topic, metadata)
        
        # Calculate weighted final score
        overall = (
            trend_score * self.SCORE_WEIGHTS["trend"] +
            emotional_score * self.SCORE_WEIGHTS["emotional"] +
            ctr_potential * self.SCORE_WEIGHTS["ctr"] +
            engagement_potential * self.SCORE_WEIGHTS["engagement"] +
            novelty_score * self.SCORE_WEIGHTS["novelty"]
        )
        
        # Build factors dict
        factors = {
            "trend_score": trend_score,
            "emotional_score": emotional_score,
            "ctr_potential": ctr_potential,
            "engagement_potential": engagement_potential,
            "novelty_score": novelty_score,
            "source_count": len(sources),
            "total_engagement": sum(s.engagement_score for s in sources),
        }
        
        # Generate reason
        reason = self._generate_reason(
            topic=topic,
            trend_score=trend_score,
            emotional_score=emotional_score,
            ctr_potential=ctr_potential,
            sources=sources,
            niche=niche,
        )
        
        return ViralityScore(
            overall=min(100, max(0, overall)),  # Clamp to 0-100
            trend_score=trend_score,
            emotional_score=emotional_score,
            ctr_potential=ctr_potential,
            engagement_potential=engagement_potential,
            novelty_score=novelty_score,
            factors=factors,
            reason=reason,
        )
    
    def _calculate_trend_score(self, sources: List[TopicSource]) -> float:
        """
        Calculate trend score based on sources.
        
        Factors:
        - Number of sources
        - Engagement on each source
        - Recency
        """
        if not sources:
            return 0.0
        
        # Base score from source count (max 40 points)
        source_count_score = min(40, len(sources) * 10)
        
        # Engagement score (max 40 points)
        if sources:
            avg_engagement = sum(s.engagement_score for s in sources) / len(sources)
            engagement_score = avg_engagement * 0.4
        else:
            engagement_score = 0
        
        # Recency score (max 20 points)
        now = datetime.utcnow()
        recency_scores = []
        for source in sources:
            age_hours = (now - source.timestamp).total_seconds() / 3600
            # Fresh topics (0-6 hours) get full points
            if age_hours < 6:
                recency_scores.append(20)
            elif age_hours < 24:
                recency_scores.append(20 * (1 - age_hours / 24))
            else:
                recency_scores.append(max(0, 20 * (1 - age_hours / 48)))
        
        recency_score = sum(recency_scores) / len(recency_scores) if recency_scores else 0
        
        return min(100, source_count_score + engagement_score + recency_score)
    
    def _calculate_emotional_score(
        self,
        topic: str,
        emotional_triggers: List[str]
    ) -> float:
        """
        Calculate emotional impact score.
        
        Analyzes topic text for emotional triggers and weights them.
        """
        if not emotional_triggers:
            # Try to detect from topic text
            emotional_triggers = self._detect_emotions_from_text(topic)
        
        if not emotional_triggers:
            return 30.0  # Base score
        
        # Calculate weighted emotional score
        total_weight = 0
        for emotion in emotional_triggers:
            emotion_lower = emotion.lower()
            weight = self.EMOTIONAL_WEIGHTS.get(emotion_lower, 0.5)
            total_weight += weight
        
        # Normalize to 0-100 (assume max 5 emotions)
        max_possible = 5 * 0.9  # 5 emotions at max weight
        normalized = (total_weight / max_possible) * 100
        
        return min(100, normalized)
    
    def _detect_emotions_from_text(self, text: str) -> List[str]:
        """Detect emotional triggers from text."""
        emotions = []
        text_lower = text.lower()
        
        # Curiosity indicators
        if any(word in text_lower for word in ["secret", "hidden", "unknown", "mystery", "revealed"]):
            emotions.append("curiosity")
        
        # Surprise indicators
        if any(word in text_lower for word in ["shocking", "surprising", "unexpected", "unbelievable"]):
            emotions.append("surprise")
        
        # Fear indicators
        if any(word in text_lower for word in ["danger", "warning", "threat", "risk", "crisis"]):
            emotions.append("fear")
        
        # Inspiration indicators
        if any(word in text_lower for word in ["inspiring", "motivation", "success", "achieve", "overcome"]):
            emotions.append("inspiration")
        
        # Urgency indicators
        if any(word in text_lower for word in ["breaking", "urgent", "now", "alert", "immediate"]):
            emotions.append("urgency")
        
        return emotions
    
    def _calculate_ctr_potential(self, topic: str) -> float:
        """
        Calculate click-through rate potential.
        
        Analyzes topic for CTR-optimized patterns.
        """
        base_score = 50.0  # Base CTR potential
        bonus = 0
        
        # Check for CTR patterns
        for pattern, pattern_bonus in self._compiled_ctr_patterns:
            if pattern.search(topic):
                bonus += pattern_bonus
        
        # Length bonus (optimal title length 40-60 chars)
        length = len(topic)
        if 40 <= length <= 60:
            bonus += 10
        elif 30 <= length <= 70:
            bonus += 5
        
        # Question bonus
        if topic.endswith("?") or topic.lower().startswith(("why ", "how ", "what ", "when ")):
            bonus += 8
        
        return min(100, base_score + bonus)
    
    def _calculate_engagement_potential(
        self,
        sources: List[TopicSource],
        topic: str
    ) -> float:
        """
        Calculate engagement potential (comments, shares, likes).
        
        Based on source engagement and topic characteristics.
        """
        base_score = 50.0
        
        # Source engagement factor
        if sources:
            avg_engagement = sum(s.engagement_score for s in sources) / len(sources)
            base_score += avg_engagement * 0.3
        
        # Controversy indicator (generates comments)
        controversy_words = ["controversial", "debate", "argument", "fight", "vs", "versus"]
        if any(word in topic.lower() for word in controversy_words):
            base_score += 15
        
        # Shareability indicators
        share_words = ["must watch", "share", "everyone needs", "viral"]
        if any(word in topic.lower() for word in share_words):
            base_score += 10
        
        return min(100, base_score)
    
    def _calculate_novelty_score(
        self,
        topic: str,
        metadata: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate novelty/uniqueness score.
        
        Fresh topics score higher.
        """
        base_score = 50.0
        
        # Check metadata for novelty indicators
        if metadata:
            # First-seen recency
            if "first_seen" in metadata:
                try:
                    first_seen = metadata["first_seen"]
                    if isinstance(first_seen, datetime):
                        age_hours = (datetime.utcnow() - first_seen).total_seconds() / 3600
                        if age_hours < 12:
                            base_score += 30
                        elif age_hours < 24:
                            base_score += 20
                        elif age_hours < 48:
                            base_score += 10
                except Exception:
                    pass
            
            # Trending velocity
            if "trend_velocity" in metadata:
                velocity = metadata["trend_velocity"]
                if velocity > 100:  # Rapidly trending
                    base_score += 25
                elif velocity > 50:
                    base_score += 15
        
        # Novelty keywords
        novelty_words = ["first time", "never before", "newly revealed", "just in", "breaking"]
        if any(word in topic.lower() for word in novelty_words):
            base_score += 20
        
        return min(100, base_score)
    
    def _generate_reason(
        self,
        topic: str,
        trend_score: float,
        emotional_score: float,
        ctr_potential: float,
        sources: List[TopicSource],
        niche: Optional[str]
    ) -> str:
        """Generate human-readable reason for virality score."""
        reasons = []
        
        # Trend assessment
        if trend_score >= 70:
            reasons.append("highly trending")
        elif trend_score >= 50:
            reasons.append("moderately trending")
        
        # Emotional assessment
        if emotional_score >= 70:
            reasons.append("strong emotional impact")
        elif emotional_score >= 50:
            reasons.append("moderate emotional appeal")
        
        # CTR assessment
        if ctr_potential >= 70:
            reasons.append("high CTR potential")
        elif ctr_potential >= 50:
            reasons.append("decent CTR potential")
        
        # Source assessment
        if len(sources) >= 5:
            reasons.append(f"validated across {len(sources)} sources")
        elif len(sources) >= 3:
            reasons.append(f"multi-source verified ({len(sources)} sources)")
        
        # Niche context
        if niche:
            reasons.append(f"strong {niche.replace('_', ' ')} content")
        
        if reasons:
            return f"Topic shows {' and '.join(reasons[:3])}"
        else:
            return "Topic has moderate viral potential"
    
    def get_score_breakdown(self, score: ViralityScore) -> Dict[str, Any]:
        """Get detailed breakdown of a virality score."""
        return {
            "overall": score.overall,
            "components": {
                "trend": {
                    "score": score.trend_score,
                    "weight": self.SCORE_WEIGHTS["trend"],
                    "contribution": score.trend_score * self.SCORE_WEIGHTS["trend"],
                },
                "emotional": {
                    "score": score.emotional_score,
                    "weight": self.SCORE_WEIGHTS["emotional"],
                    "contribution": score.emotional_score * self.SCORE_WEIGHTS["emotional"],
                },
                "ctr": {
                    "score": score.ctr_potential,
                    "weight": self.SCORE_WEIGHTS["ctr"],
                    "contribution": score.ctr_potential * self.SCORE_WEIGHTS["ctr"],
                },
                "engagement": {
                    "score": score.engagement_potential,
                    "weight": self.SCORE_WEIGHTS["engagement"],
                    "contribution": score.engagement_potential * self.SCORE_WEIGHTS["engagement"],
                },
                "novelty": {
                    "score": score.novelty_score,
                    "weight": self.SCORE_WEIGHTS["novelty"],
                    "contribution": score.novelty_score * self.SCORE_WEIGHTS["novelty"],
                },
            },
            "factors": score.factors,
            "reason": score.reason,
        }
