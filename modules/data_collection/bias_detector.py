"""
Bias Detection Module - Simple language analysis for media bias flags.

Detects:
- Loaded/emotional language
- One-sided sourcing
- Propaganda techniques
- Sensationalism

This helps users understand potential bias in sources without making
political determinations (left/right) - just flagging manipulation techniques.
"""

import re
from typing import Optional
from loguru import logger


# Emotional/loaded words that indicate bias
LOADED_WORDS = {
    # Fear/Threat
    "massacre", "slaughter", "bloodbath", "carnage", "devastating",
    "catastrophic", "apocalyptic", "terrifying", "horrifying",
    
    # Judgment (without evidence)
    "terrorist", "extremist", "radical", "fanatic", "zealot",
    "dictator", "tyrant", "oppressor", "aggressor",
    
    # Emotional manipulation
    "shocking", "outrageous", "disgraceful", "appalling", "sickening",
    "heartbreaking", "tragic", "unbelievable", "incredible",
    
    # Absolutist language
    "always", "never", "everyone", "no one", "all", "none",
    "definitely", "undoubtedly", "clearly", "obviously",
    
    # Propaganda markers
    "regime", "junta", "axis", "evil", "crusade", "jihad",
    "ethnic cleansing", "genocide", "war crimes",
}

# Propaganda technique patterns
PROPAGANDA_PATTERNS = [
    r"\b(us vs them|with us or against us)\b",  # False dichotomy
    r"\b(slippery slope|domino effect)\b",       # Slippery slope
    r"\b(everyone knows|most people agree)\b",   # Bandwagon
    r"\b(science says|experts agree)\b",         # Appeal to authority (vague)
    r"\b(studies show|research proves)\b",       # Vague reference
    r"\b(clearly|obviously|undoubtedly)\b",      # Presumptive language
    r"\b(fail|failure|failed|disaster)\b",       # Disaster framing
]

# Sensationalism indicators
SENSATIONAL_PATTERNS = [
    r"!{2,}",                    # Multiple exclamation marks
    r"\?{2,}",                   # Multiple question marks
    r"\b(BREAKING|URGENT|ALERT)\b",  # Alarmist labels
    r"\b(YOU WON'T BELIEVE|SHOCKING)\b",  # Clickbait
    r"\b(MUST SEE|MUST WATCH)\b",  # Urgency
]


class BiasAnalysis:
    """Result of bias analysis on a text."""
    
    def __init__(
        self,
        loaded_language: bool = False,
        one_sided_sources: bool = False,
        unverified_claims: bool = False,
        propaganda_patterns: bool = False,
        sensationalism: bool = False,
        loaded_word_count: int = 0,
        bias_score: float = 0.0,
    ):
        self.loaded_language = loaded_language
        self.one_sided_sources = one_sided_sources
        self.unverified_claims = unverified_claims
        self.propaganda_patterns = propaganda_patterns
        self.sensationalism = sensationalism
        self.loaded_word_count = loaded_word_count
        self.bias_score = bias_score  # 0-1, higher = more biased

    def to_dict(self) -> dict:
        return {
            "loaded_language": self.loaded_language,
            "one_sided_sources": self.one_sided_sources,
            "unverified_claims": self.unverified_claims,
            "propaganda_patterns": self.propaganda_patterns,
            "sensationalism": self.sensationalism,
            "loaded_word_count": self.loaded_word_count,
            "bias_score": round(self.bias_score, 3),
        }

    def has_flags(self) -> bool:
        """Check if any bias flags were raised."""
        return any([
            self.loaded_language,
            self.one_sided_sources,
            self.unverified_claims,
            self.propaganda_patterns,
            self.sensationalism,
        ])


class BiasDetector:
    """
    Simple bias detection through language analysis.
    
    Does NOT detect political bias (left/right/pro-X/pro-Y).
    Instead, flags manipulation techniques that appear across all media.
    """

    def __init__(self):
        self.loaded_words = LOADED_WORDS
        self.propaganda_patterns = [
            re.compile(p, re.IGNORECASE) for p in PROPAGANDA_PATTERNS
        ]
        self.sensational_patterns = [
            re.compile(p, re.IGNORECASE) for p in SENSATIONAL_PATTERNS
        ]

    def analyze(self, text: str, sources: list = None) -> BiasAnalysis:
        """
        Analyze text for bias indicators.
        
        Args:
            text: Article/tweet/post content to analyze
            sources: List of source types (for one-sided detection)
        """
        if not text or len(text) < 50:
            return BiasAnalysis()

        text_lower = text.lower()
        flags = {
            "loaded_word_count": 0,
            "loaded_language": False,
            "propaganda_patterns": False,
            "sensationalism": False,
            "one_sided_sources": False,
            "unverified_claims": False,
        }

        # 1. Check for loaded words
        loaded_count = 0
        for word in self.loaded_words:
            if word in text_lower:
                loaded_count += 1
        
        flags["loaded_word_count"] = loaded_count
        flags["loaded_language"] = loaded_count >= 3  # 3+ loaded words

        # 2. Check for propaganda patterns
        propaganda_matches = 0
        for pattern in self.propaganda_patterns:
            if pattern.search(text):
                propaganda_matches += 1
        
        flags["propaganda_patterns"] = propaganda_matches >= 2

        # 3. Check for sensationalism
        sensational_matches = 0
        for pattern in self.sensational_patterns:
            if pattern.search(text):
                sensational_matches += 1
        
        flags["sensationalism"] = sensational_matches >= 1

        # 4. Check for one-sided sourcing (if sources provided)
        if sources:
            source_types = [s.get("source_category", "") for s in sources]
            # All from same category = potentially one-sided
            if len(set(source_types)) == 1 and len(sources) >= 3:
                flags["one_sided_sources"] = True

        # 5. Check for unverified claims
        unverified_markers = [
            "reportedly", "allegedly", "sources say", "according to reports",
            "it is believed", "rumors suggest", "unconfirmed reports",
        ]
        unverified_count = sum(1 for marker in unverified_markers if marker in text_lower)
        flags["unverified_claims"] = unverified_count >= 2

        # Calculate overall bias score (0-1)
        score = 0.0
        if flags["loaded_language"]:
            score += 0.25
        if flags["propaganda_patterns"]:
            score += 0.25
        if flags["sensationalism"]:
            score += 0.20
        if flags["one_sided_sources"]:
            score += 0.15
        if flags["unverified_claims"]:
            score += 0.15
        
        # Cap at 1.0
        flags["bias_score"] = min(score, 1.0)

        return BiasAnalysis(**flags)

    def analyze_multiple_sources(
        self, 
        sources: list
    ) -> dict[str, BiasAnalysis]:
        """
        Analyze bias across multiple sources for the same topic.
        
        Returns dict mapping source URL → BiasAnalysis
        """
        results = {}
        
        for source in sources:
            text = source.get("snippet", "") or source.get("title", "")
            if not text:
                continue
            
            analysis = self.analyze(text, [source])
            results[source.get("url", str(hash(text)))] = analysis

        return results

    def get_perspective_diversity(self, sources: list) -> dict:
        """
        Check if sources represent diverse perspectives.
        
        Returns:
            {
                "diverse": bool,
                "categories": list of source categories,
                "mainstream_count": int,
                "independent_count": int,
                "social_count": int,
            }
        """
        categories = {}
        
        for source in sources:
            cat = source.get("source_category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        # Diverse if 2+ different categories represented
        diverse = len(categories) >= 2

        return {
            "diverse": diverse,
            "categories": list(categories.keys()),
            "mainstream_count": categories.get("mainstream", 0),
            "independent_count": categories.get("independent", 0),
            "social_count": categories.get("social", 0) + categories.get("eyewitness", 0),
            "community_count": categories.get("community", 0),
        }


# Convenience function
def detect_bias(text: str, sources: list = None) -> BiasAnalysis:
    """Quick bias detection for a single text."""
    detector = BiasDetector()
    return detector.analyze(text, sources)
