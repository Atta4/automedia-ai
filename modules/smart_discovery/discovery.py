"""
Smart Topic Discovery Engine

Main orchestrator for viral topic discovery across multiple sources.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from config.niche_config import niche_config_manager, NicheType
from .models import (
    DiscoveredTopic,
    TopicSource,
    TopicSourcePlatform,
    ViralityScore,
    TopicDiscoveryResult,
    TopicGenerationRequest,
    TrendingTopic,
)
from .virality_calculator import ViralityCalculator


class SmartTopicDiscoveryEngine:
    """
    Smart topic discovery engine for viral content.
    
    Features:
    - Multi-source trend aggregation
    - Niche-specific discovery
    - Virality scoring
    - CTR pattern analysis
    - Emotional trigger detection
    """
    
    def __init__(self, db=None, openai_client=None):
        """
        Initialize the discovery engine.
        
        Args:
            db: MongoDB database connection
            openai_client: OpenAI client for AI-powered topic generation
        """
        self._db = db
        self._openai_client = openai_client
        self._virality_calculator = ViralityCalculator()
        self._niche_config_manager = niche_config_manager
    
    async def discover_topics(
        self,
        request: TopicGenerationRequest
    ) -> TopicDiscoveryResult:
        """
        Discover viral topics for a niche.
        
        Args:
            request: Topic generation request
            
        Returns:
            TopicDiscoveryResult with discovered topics
        """
        start_time = datetime.utcnow()
        
        # Get niche configuration
        niche_config = self._niche_config_manager.get_niche_by_value(request.niche)
        if not niche_config:
            # Fall back to trending/viral niche
            niche_config = self._niche_config_manager.get_niche_by_value("trending_viral")
            request.niche = "trending_viral"
        
        # Determine sources to check
        sources_to_check = self._get_sources_for_niche(request.niche)
        
        # Collect trending topics from all sources
        trending_topics = await self._collect_trending_topics(
            niche=request.niche,
            sources=sources_to_check,
            region=request.region,
            language=request.language,
            focus_keywords=request.focus_keywords,
        )
        
        # Process and score topics
        discovered_topics = await self._process_trending_topics(
            trending_topics=trending_topics,
            niche=request.niche,
            min_virality_score=request.min_virality_score,
            exclude_keywords=request.exclude_keywords,
        )
        
        # Sort by virality score
        discovered_topics.sort(key=lambda t: t.virality_score.overall, reverse=True)
        
        # Limit to max topics
        discovered_topics = discovered_topics[:request.max_topics]
        
        # Calculate average virality
        if discovered_topics:
            avg_virality = sum(
                t.virality_score.overall for t in discovered_topics
            ) / len(discovered_topics)
        else:
            avg_virality = 0
        
        # Build result
        result = TopicDiscoveryResult(
            niche=request.niche,
            topics=discovered_topics,
            total_discovered=len(discovered_topics),
            total_validated=sum(1 for t in discovered_topics if t.is_validated),
            avg_virality_score=avg_virality,
            discovery_duration_sec=(datetime.utcnow() - start_time).total_seconds(),
            sources_checked=len(sources_to_check),
        )
        
        return result
    
    def _get_sources_for_niche(self, niche: str) -> List[str]:
        """Get recommended sources for a niche."""
        config = self._niche_config_manager.get_niche_by_value(niche)
        if not config:
            return ["youtube", "twitter", "reddit"]
        
        # Combine primary and secondary sources
        all_sources = config.primary_sources + config.secondary_sources
        return list(set(all_sources))  # Remove duplicates
    
    async def _collect_trending_topics(
        self,
        niche: str,
        sources: List[str],
        region: str,
        language: str,
        focus_keywords: Optional[List[str]] = None
    ) -> List[TrendingTopic]:
        """
        Collect trending topics from multiple sources.
        
        This is a simulation layer that would integrate with actual APIs.
        In production, this would call:
        - YouTube Data API
        - Twitter API
        - Reddit API
        - Google Trends
        - News APIs
        """
        trending_topics = []
        
        # Focus keywords injection (always include these)
        if focus_keywords:
            for keyword in focus_keywords[:5]:  # Limit to 5 focus keywords
                trending_topics.append(TrendingTopic(
                    platform=TopicSourcePlatform.GOOGLE_TRENDS,
                    title=f"Focus: {keyword}",
                    keyword=keyword,
                    trend_score=85.0,  # High priority
                    engagement=1000,
                    metadata={"is_focus_keyword": True}
                ))
        
        # Niche-specific focus keywords from config
        config = self._niche_config_manager.get_niche_by_value(niche)
        if config and config.focus_keywords:
            for keyword in random.sample(
                config.focus_keywords,
                min(3, len(config.focus_keywords))
            ):
                trending_topics.append(TrendingTopic(
                    platform=TopicSourcePlatform.GOOGLE_TRENDS,
                    title=f"Trending in {niche}: {keyword}",
                    keyword=keyword,
                    trend_score=75.0,
                    engagement=500,
                    metadata={"from_niche_config": True}
                ))
        
        # Simulated trending topics from various platforms
        # In production, these would be real API calls
        simulated_topics = await self._generate_simulated_trending_topics(
            niche=niche,
            count=10,
            region=region,
        )
        trending_topics.extend(simulated_topics)
        
        return trending_topics
    
    async def _generate_simulated_trending_topics(
        self,
        niche: str,
        count: int,
        region: str
    ) -> List[TrendingTopic]:
        """
        Generate simulated trending topics for a niche.
        
        In production, this would be replaced with actual API calls.
        For now, generates AI-style topics based on niche.
        """
        # Topic templates by niche
        niche_templates = {
            "motivation": [
                "Why Successful People Wake Up at 5 AM",
                "The Morning Routine That Changed My Life",
                "3 Habits That Will Make You Unstoppable",
                "This Mindset Shift Will Change Everything",
                "The Truth About Overnight Success",
            ],
            "finance": [
                "Why The Stock Market Is About To Crash",
                "Passive Income Ideas That Actually Work",
                "The Investment Strategy Billionaires Use",
                "Crypto: What's Next After The Crash",
                "How To Build Wealth In Your 20s",
            ],
            "ai_tech": [
                "This New AI Can Do What Humans Can't",
                "Why AI Will Replace These Jobs First",
                "The AI Tool That's Breaking The Internet",
                "ChatGPT Just Got A Massive Upgrade",
                "The Future Of AI Is Scarier Than You Think",
            ],
            "islamic": [
                "The Power of Surah Al-Fatiha",
                "Prophet Muhammad's ﷺ Morning Routine",
                "This Dua Will Change Your Life",
                "The Story of Prophet Yusuf AS",
                "Why Allah Tests Those He Loves",
            ],
            "health_fitness": [
                "The Workout Mistake Ruining Your Gains",
                "Why You're Not Losing Weight",
                "The Science of Building Muscle",
                "This Exercise Burns 10x More Fat",
                "What Happens To Your Body When You Quit Sugar",
            ],
            "history": [
                "The Dark Truth About Ancient Rome",
                "What Really Happened To The Dinosaurs",
                "The Most Brutal Empire In History",
                "The War That Changed The World",
                "The Mystery That Historians Can't Solve",
            ],
            "facts_did_you_know": [
                "10 Facts That Sound Fake But Are True",
                "The Strangest Law In Every Country",
                "Science Facts That Will Blow Your Mind",
                "Things You've Been Doing Wrong Your Whole Life",
                "The Most Dangerous Places On Earth",
            ],
            "horror_stories": [
                "The Haunting That Fooled The World",
                "True Crime: The Case Nobody Can Solve",
                "The Scariest Urban Legend Is Real",
                "What Really Happened That Night",
                "The Ghost Story That's Actually True",
            ],
            "relationships": [
                "Why Men Pull Away (And What To Do)",
                "The Psychology of Attraction",
                "Signs They're Not The One",
                "Why Your Relationship Feels Hard",
                "The Secret To Making Him Obsessed",
            ],
            "business": [
                "How This CEO Built A Billion Dollar Company",
                "The Business Mistake That Cost Millions",
                "Why Most Startups Fail In Year One",
                "The Marketing Strategy That Changed Everything",
                "How To Scale Your Business To 7 Figures",
            ],
            "trending_viral": [
                "This Video Is Breaking The Internet",
                "Everyone Is Talking About This",
                "The Trend That's Taking Over TikTok",
                "You Won't Believe What Just Happened",
                "This Is The Most Viral Thing Ever",
            ],
            "current_affairs": [
                "Breaking: Major Development In The Conflict",
                "Why This Political Decision Matters",
                "The News They Don't Want You To See",
                "What Just Happened Will Shock You",
                "The Real Story Behind The Headlines",
            ],
        }
        
        # Get templates for niche (or use trending_viral as fallback)
        templates = niche_templates.get(niche, niche_templates["trending_viral"])
        
        # Generate topics
        topics = []
        platforms = [
            TopicSourcePlatform.YOUTUBE,
            TopicSourcePlatform.TWITTER,
            TopicSourcePlatform.REDDIT,
            TopicSourcePlatform.TIKTOK,
        ]
        
        for i, title in enumerate(templates[:count]):
            platform = random.choice(platforms)
            topics.append(TrendingTopic(
                platform=platform,
                title=title,
                keyword=self._extract_keyword(title),
                trend_score=random.uniform(60, 95),
                engagement=random.randint(100, 10000),
                url=f"https://{platform.value}.com/trending/{i}",
                metadata={
                    "simulated": True,
                    "niche": niche,
                }
            ))
        
        return topics
    
    def _extract_keyword(self, title: str) -> str:
        """Extract a keyword/slug from a title."""
        # Simple keyword extraction
        words = title.lower().split()
        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return "_".join(keywords[:5])  # First 5 significant words
    
    async def _process_trending_topics(
        self,
        trending_topics: List[TrendingTopic],
        niche: str,
        min_virality_score: int,
        exclude_keywords: List[str]
    ) -> List[DiscoveredTopic]:
        """
        Process trending topics and calculate virality scores.
        
        Filters, validates, and scores topics.
        """
        discovered = []
        
        # Get niche emotional triggers for scoring
        niche_config = self._niche_config_manager.get_niche_by_value(niche)
        niche_emotions = []
        if niche_config:
            niche_emotions = [e.value for e in niche_config.emotional_triggers]
        
        for topic in trending_topics:
            # Check exclusion list
            if any(exclude.lower() in topic.keyword.lower() for exclude in exclude_keywords):
                continue
            
            # Create topic source
            source = TopicSource(
                platform=topic.platform,
                url=topic.url,
                title=topic.title,
                engagement_score=min(100, topic.engagement / 100) if topic.engagement else 50,
                reach=topic.engagement,
                timestamp=datetime.utcnow(),
                metadata=topic.metadata,
            )
            
            # Detect emotional triggers
            emotional_triggers = self._detect_emotional_triggers(
                topic.title,
                niche_emotions
            )
            
            # Calculate virality score
            virality_score = self._virality_calculator.calculate(
                topic=topic.title,
                sources=[source],
                emotional_triggers=emotional_triggers,
                niche=niche,
                metadata=topic.metadata,
            )
            
            # Filter by minimum virality
            if virality_score.overall < min_virality_score:
                continue
            
            # Detect CTR patterns
            ctr_patterns = self._detect_ctr_patterns(topic.title)
            
            # Validate topic
            is_validated = len(emotional_triggers) >= 1 and virality_score.overall >= 60
            validation_reason = self._generate_validation_reason(
                is_validated,
                emotional_triggers,
                virality_score,
            )
            
            # Create discovered topic
            discovered_topic = DiscoveredTopic(
                niche=niche,
                topic=topic.title,
                normalized_keyword=topic.keyword,
                virality_score=virality_score,
                sources=[source],
                source_count=1,
                emotional_triggers=emotional_triggers,
                primary_emotion=emotional_triggers[0] if emotional_triggers else None,
                ctr_patterns=ctr_patterns,
                hook_potential=virality_score.ctr_potential,
                is_validated=is_validated,
                validation_reason=validation_reason,
                tags=self._generate_tags(topic.title, niche),
                metadata=topic.metadata,
            )
            
            discovered.append(discovered_topic)
        
        return discovered
    
    def _detect_emotional_triggers(
        self,
        title: str,
        niche_emotions: List[str]
    ) -> List[str]:
        """Detect emotional triggers in a title."""
        triggers = []
        title_lower = title.lower()
        
        # Emotion keyword mappings
        emotion_keywords = {
            "curiosity": ["secret", "hidden", "unknown", "mystery", "revealed", "truth"],
            "surprise": ["shocking", "surprising", "unexpected", "unbelievable", "mind-blowing"],
            "shock": ["shocked", "stunned", "jaw-dropping", "horrifying"],
            "fear": ["danger", "warning", "threat", "crisis", "terrifying", "scary"],
            "inspiration": ["inspiring", "motivation", "success", "achieve", "overcome", "powerful"],
            "anger": ["outrage", "angry", "furious", "controversial", "scandal"],
            "joy": ["amazing", "wonderful", "beautiful", "heartwarming", "incredible"],
            "urgency": ["breaking", "urgent", "now", "alert", "immediate", "just in"],
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                triggers.append(emotion)
            elif emotion in niche_emotions and emotion in title_lower:
                triggers.append(emotion)
        
        return triggers
    
    def _detect_ctr_patterns(self, title: str) -> List[str]:
        """Detect CTR-optimized patterns in a title."""
        patterns = []
        title_lower = title.lower()
        
        if any(word in title_lower for word in ["you won't believe", "unbelievable"]):
            patterns.append("you_wont_believe")
        
        if any(word in title_lower for word in ["this is why", "that's why"]):
            patterns.append("this_is_why")
        
        if any(word in title_lower for word in ["top", "best", "worst"]):
            patterns.append("list_format")
        
        if any(word in title_lower for word in ["secret", "secrets", "hidden"]):
            patterns.append("curiosity_gap")
        
        if title.endswith("?") or title_lower.startswith(("why ", "how ", "what ")):
            patterns.append("question")
        
        if any(word.isdigit() for word in title.split()):
            patterns.append("numbered")
        
        return patterns
    
    def _generate_validation_reason(
        self,
        is_validated: bool,
        emotional_triggers: List[str],
        virality_score: ViralityScore
    ) -> str:
        """Generate validation reason string."""
        if not is_validated:
            return "Does not meet virality threshold"
        
        reasons = []
        
        if len(emotional_triggers) >= 2:
            reasons.append(f"strong emotional triggers ({len(emotional_triggers)})")
        elif len(emotional_triggers) == 1:
            reasons.append(f"emotional trigger: {emotional_triggers[0]}")
        
        if virality_score.overall >= 80:
            reasons.append("exceptional virality score")
        elif virality_score.overall >= 70:
            reasons.append("high virality potential")
        
        return f"✓ Validated: {', '.join(reasons)}" if reasons else "✓ Validated"
    
    def _generate_tags(self, title: str, niche: str) -> List[str]:
        """Generate relevant tags for a topic."""
        tags = []
        
        # Niche tags
        niche_tag = niche.replace("_", "")
        tags.append(niche_tag)
        tags.append(f"{niche}content")
        tags.append(f"{niche}videos")
        
        # Topic-based tags
        words = title.lower().split()
        significant_words = [
            w for w in words
            if len(w) > 3 and w not in {"this", "that", "with", "from", "have", "will"}
        ]
        tags.extend(significant_words[:5])
        
        # Viral tags
        tags.extend(["viral", "trending", "fyp"])
        
        return list(set(tags))  # Remove duplicates
    
    async def discover_single_topic(
        self,
        niche: str,
        topic_title: str
    ) -> Optional[DiscoveredTopic]:
        """
        Discover and score a single topic.
        
        Useful for validating user-provided topics.
        """
        # Create a simulated trending topic
        trending = TrendingTopic(
            platform=TopicSourcePlatform.YOUTUBE,
            title=topic_title,
            keyword=self._extract_keyword(topic_title),
            trend_score=70.0,
            engagement=500,
        )
        
        # Process it
        topics = await self._process_trending_topics(
            trending_topics=[trending],
            niche=niche,
            min_virality_score=0,  # No minimum
            exclude_keywords=[],
        )
        
        return topics[0] if topics else None
    
    def get_virality_breakdown(self, topic: DiscoveredTopic) -> Dict[str, Any]:
        """Get detailed virality breakdown for a topic."""
        return self._virality_calculator.get_score_breakdown(topic.virality_score)
