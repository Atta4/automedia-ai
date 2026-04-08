"""
Algorithm Optimization Module

Optimizes content for platform algorithms (YouTube, Shorts, Reels).
Generates CTR-optimized titles, SEO descriptions, and search-optimized tags.
"""

from .optimizer import AlgorithmOptimizer
from .models import VideoMetadata, TitleVariant, SEOScore, MetadataGenerationRequest

__all__ = [
    "AlgorithmOptimizer",
    "VideoMetadata",
    "TitleVariant",
    "SEOScore",
    "MetadataGenerationRequest",
]
