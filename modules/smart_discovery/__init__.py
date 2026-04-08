"""
Smart Topic Discovery Engine

Generates viral-potential topics with virality scoring based on:
- Trend awareness from multiple sources
- Emotional triggers
- CTR patterns
- Niche-specific optimization
"""

from .discovery import SmartTopicDiscoveryEngine
from .models import DiscoveredTopic, ViralityScore, TopicSource, TopicGenerationRequest, TopicDiscoveryResult
from .virality_calculator import ViralityCalculator

__all__ = [
    "SmartTopicDiscoveryEngine",
    "DiscoveredTopic",
    "ViralityScore",
    "TopicSource",
    "ViralityCalculator",
    "TopicGenerationRequest",
    "TopicDiscoveryResult",
]
