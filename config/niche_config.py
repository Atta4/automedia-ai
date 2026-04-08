"""
Multi-Niche Viral Content Engine - Configuration System

Defines all supported niches with their specific strategies, tones, and optimization rules.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class NicheType(str, Enum):
    """Supported content niches."""
    MOTIVATION = "motivation"
    FINANCE = "finance"
    AI_TECH = "ai_tech"
    ISLAMIC = "islamic"
    HEALTH_FITNESS = "health_fitness"
    HISTORY = "history"
    FACTS_DID_YOU_KNOW = "facts_did_you_know"
    HORROR_STORIES = "horror_stories"
    RELATIONSHIPS = "relationships"
    BUSINESS = "business"
    TRENDING_VIRAL = "trending_viral"
    CURRENT_AFFAIRS = "current_affairs"  # Legacy niche


class EmotionalTrigger(str, Enum):
    """Emotional triggers for virality."""
    CURIOSITY = "curiosity"
    FEAR = "fear"
    SHOCK = "shock"
    INSPIRATION = "inspiration"
    ANGER = "anger"
    JOY = "joy"
    SURPRISE = "surprise"
    URGENCY = "urgency"


class HookStrategy(str, Enum):
    """Hook strategies for viral openings."""
    YOU_WONT_BELIEVE = "you_wont_believe"
    THIS_IS_WHY = "this_is_why"
    TOP_SECRETS = "top_secrets"
    STORY_BASED = "story_based"
    QUESTION_BASED = "question_based"
    STATISTIC_SHOCK = "statistic_shock"
    CONTRARIAN = "contrarian"
    PATTERN_INTERRUPT = "pattern_interrupt"


class ContentTone(str, Enum):
    """Content tone profiles."""
    URGENT = "urgent"
    INSPIRING = "inspiring"
    MYSTERIOUS = "mysterious"
    AUTHORITATIVE = "authoritative"
    CONVERSATIONAL = "conversational"
    DRAMATIC = "dramatic"
    EDUCATIONAL = "educational"
    ENTERTAINING = "entertaining"


class NicheConfig(BaseModel):
    """Configuration for a single niche."""
    
    niche: NicheType
    display_name: str
    description: str
    
    # Discovery settings
    primary_sources: List[str] = Field(default_factory=list)
    secondary_sources: List[str] = Field(default_factory=list)
    focus_keywords: List[str] = Field(default_factory=list)
    min_sources_to_validate: int = 2
    virality_threshold: int = 60
    
    # Content settings
    default_tones: List[ContentTone] = Field(default_factory=list)
    hook_strategies: List[HookStrategy] = Field(default_factory=list)
    emotional_triggers: List[EmotionalTrigger] = Field(default_factory=list)
    
    # Script settings
    target_duration_sec: int = 90
    hook_duration_sec: int = 3
    retention_hook_interval_sec: int = 5
    pacing: str = "fast"  # slow, medium, fast
    
    # Voice settings (OpenAI TTS)
    preferred_voices: List[str] = Field(default_factory=list)
    voice_speed: float = 1.0
    
    # Visual settings
    visual_style: str = "dynamic"  # static, dynamic, cinematic
    color_palette: List[str] = Field(default_factory=list)
    
    # Algorithm optimization
    category_id: str = "25"  # YouTube category
    optimal_posting_times: List[str] = Field(default_factory=list)  # ISO format hours
    cta_style: str = "subscribe"  # subscribe, comment, share, like
    
    # Upload strategy
    daily_upload_limit: int = 5
    upload_priority: int = 1  # 1 = highest
    
    # Variation settings
    title_patterns: List[str] = Field(default_factory=list)
    thumbnail_styles: List[str] = Field(default_factory=list)


class NicheConfigManager:
    """Manages all niche configurations and provides lookup utilities."""
    
    def __init__(self):
        self._configs: Dict[NicheType, NicheConfig] = {}
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialize default configurations for all supported niches."""
        
        # MOTIVATION
        self._configs[NicheType.MOTIVATION] = NicheConfig(
            niche=NicheType.MOTIVATION,
            display_name="Motivation & Self-Improvement",
            description="Inspirational content to motivate and uplift viewers",
            primary_sources=["youtube", "reddit", "twitter"],
            secondary_sources=["rss", "telegram"],
            focus_keywords=[
                "motivation", "success mindset", "self improvement", 
                "personal growth", "discipline", "goals", "habits"
            ],
            min_sources_to_validate=2,
            virality_threshold=65,
            default_tones=[ContentTone.INSPIRING, ContentTone.URGENT],
            hook_strategies=[
                HookStrategy.THIS_IS_WHY,
                HookStrategy.TOP_SECRETS,
                HookStrategy.STORY_BASED
            ],
            emotional_triggers=[
                EmotionalTrigger.INSPIRATION,
                EmotionalTrigger.URGENCY,
                EmotionalTrigger.CURIOSITY
            ],
            target_duration_sec=120,
            hook_duration_sec=3,
            pacing="fast",
            preferred_voices=["onyx", "echo"],
            voice_speed=1.05,
            visual_style="cinematic",
            color_palette=["#FF6B35", "#004E89", "#FFD23F"],
            category_id="22",  # People & Blogs
            optimal_posting_times=["06:00", "12:00", "18:00", "21:00"],
            cta_style="comment",
            daily_upload_limit=4,
            upload_priority=2,
            title_patterns=[
                "Why {topic} Will Change Your Life",
                "The {number} {topic} Secrets Nobody Tells You",
                "This {topic} Advice Changed Everything"
            ],
            thumbnail_styles=["bold_text", "contrast_face", "symbolic"]
        )
        
        # FINANCE
        self._configs[NicheType.FINANCE] = NicheConfig(
            niche=NicheType.FINANCE,
            display_name="Finance & Money",
            description="Financial advice, investment tips, and money strategies",
            primary_sources=["youtube", "twitter", "rss"],
            secondary_sources=["reddit", "newsapi"],
            focus_keywords=[
                "investing", "stock market", "crypto", "personal finance",
                "passive income", "financial freedom", "money tips"
            ],
            min_sources_to_validate=2,
            virality_threshold=70,
            default_tones=[ContentTone.AUTHORITATIVE, ContentTone.EDUCATIONAL],
            hook_strategies=[
                HookStrategy.STATISTIC_SHOCK,
                HookStrategy.CONTRARIAN,
                HookStrategy.THIS_IS_WHY
            ],
            emotional_triggers=[
                EmotionalTrigger.URGENCY,
                EmotionalTrigger.FEAR,
                EmotionalTrigger.CURIOSITY
            ],
            target_duration_sec=150,
            hook_duration_sec=4,
            pacing="medium",
            preferred_voices=["echo", "onyx"],
            voice_speed=1.0,
            visual_style="dynamic",
            color_palette=["#00C853", "#2962FF", "#FFD600"],
            category_id="27",  # Education
            optimal_posting_times=["07:00", "12:00", "17:00"],
            cta_style="subscribe",
            daily_upload_limit=3,
            upload_priority=1,
            title_patterns=[
                "Why {topic} Is Your Best Investment in {year}",
                "The Truth About {topic} They Don't Want You to Know",
                "How I Made ${amount} with {topic}"
            ],
            thumbnail_styles=["money_focus", "graph_chart", "lifestyle"]
        )
        
        # AI / TECH
        self._configs[NicheType.AI_TECH] = NicheConfig(
            niche=NicheType.AI_TECH,
            display_name="AI & Technology",
            description="Latest AI tools, tech news, and future innovations",
            primary_sources=["youtube", "twitter", "reddit"],
            secondary_sources=["rss", "newsapi"],
            focus_keywords=[
                "artificial intelligence", "AI tools", "ChatGPT", "tech news",
                "machine learning", "automation", "future tech"
            ],
            min_sources_to_validate=2,
            virality_threshold=75,
            default_tones=[ContentTone.EDUCATIONAL, ContentTone.ENTERTAINING],
            hook_strategies=[
                HookStrategy.YOU_WONT_BELIEVE,
                HookStrategy.THIS_IS_WHY,
                HookStrategy.PATTERN_INTERRUPT
            ],
            emotional_triggers=[
                EmotionalTrigger.SURPRISE,
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.URGENCY
            ],
            target_duration_sec=120,
            hook_duration_sec=3,
            pacing="fast",
            preferred_voices=["alloy", "echo"],
            voice_speed=1.1,
            visual_style="cinematic",
            color_palette=["#6366F1", "#8B5CF6", "#EC4899"],
            category_id="28",  # Science & Technology
            optimal_posting_times=["09:00", "14:00", "19:00"],
            cta_style="comment",
            daily_upload_limit=5,
            upload_priority=1,
            title_patterns=[
                "This New AI {topic} Will Blow Your Mind",
                "Why {topic} Changes Everything",
                "The Future of {topic} Is Here"
            ],
            thumbnail_styles=["tech_glow", "ai_robot", "futuristic"]
        )
        
        # ISLAMIC
        self._configs[NicheType.ISLAMIC] = NicheConfig(
            niche=NicheType.ISLAMIC,
            display_name="Islamic Content",
            description="Islamic teachings, reminders, and spiritual content",
            primary_sources=["youtube", "twitter", "telegram"],
            secondary_sources=["rss"],
            focus_keywords=[
                "islam", "quran", "hadith", "islamic reminders",
                "dua", "prophetic stories", "islamic history"
            ],
            min_sources_to_validate=2,
            virality_threshold=60,
            default_tones=[ContentTone.INSPIRING, ContentTone.AUTHORITATIVE],
            hook_strategies=[
                HookStrategy.STORY_BASED,
                HookStrategy.QUESTION_BASED,
                HookStrategy.THIS_IS_WHY
            ],
            emotional_triggers=[
                EmotionalTrigger.INSPIRATION,
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.JOY
            ],
            target_duration_sec=90,
            hook_duration_sec=4,
            pacing="medium",
            preferred_voices=["onyx", "nova"],
            voice_speed=0.95,
            visual_style="cinematic",
            color_palette=["#059669", "#D97706", "#1F2937"],
            category_id="22",  # People & Blogs
            optimal_posting_times=["05:00", "12:00", "18:00"],
            cta_style="share",
            daily_upload_limit=3,
            upload_priority=2,
            title_patterns=[
                "The Beautiful Story of {topic}",
                "Why Every Muslim Should Know About {topic}",
                "Powerful Reminder About {topic}"
            ],
            thumbnail_styles=["calligraphy", "mosque", "nature"]
        )
        
        # HEALTH & FITNESS
        self._configs[NicheType.HEALTH_FITNESS] = NicheConfig(
            niche=NicheType.HEALTH_FITNESS,
            display_name="Health & Fitness",
            description="Workout tips, nutrition advice, and wellness content",
            primary_sources=["youtube", "reddit", "twitter"],
            secondary_sources=["rss", "newsapi"],
            focus_keywords=[
                "workout", "fitness", "nutrition", "weight loss",
                "muscle building", "healthy lifestyle", "exercise"
            ],
            min_sources_to_validate=2,
            virality_threshold=65,
            default_tones=[ContentTone.INSPIRING, ContentTone.EDUCATIONAL],
            hook_strategies=[
                HookStrategy.THIS_IS_WHY,
                HookStrategy.TOP_SECRETS,
                HookStrategy.STATISTIC_SHOCK
            ],
            emotional_triggers=[
                EmotionalTrigger.INSPIRATION,
                EmotionalTrigger.URGENCY,
                EmotionalTrigger.FEAR
            ],
            target_duration_sec=120,
            hook_duration_sec=3,
            pacing="fast",
            preferred_voices=["nova", "alloy"],
            voice_speed=1.05,
            visual_style="dynamic",
            color_palette=["#EF4444", "#10B981", "#3B82F6"],
            category_id="17",  # Sports
            optimal_posting_times=["06:00", "12:00", "17:00"],
            cta_style="like",
            daily_upload_limit=4,
            upload_priority=2,
            title_patterns=[
                "The {number} {topic} Mistakes You're Making",
                "How {topic} Transformed My Body",
                "Science-Backed {topic} Secrets"
            ],
            thumbnail_styles=["before_after", "action_shot", "transformation"]
        )
        
        # HISTORY
        self._configs[NicheType.HISTORY] = NicheConfig(
            niche=NicheType.HISTORY,
            display_name="History & Documentaries",
            description="Historical events, documentaries, and untold stories",
            primary_sources=["youtube", "reddit", "rss"],
            secondary_sources=["newsapi"],
            focus_keywords=[
                "history", "historical events", "ancient civilizations",
                "world war", "historical figures", "untold stories"
            ],
            min_sources_to_validate=2,
            virality_threshold=60,
            default_tones=[ContentTone.DRAMATIC, ContentTone.EDUCATIONAL],
            hook_strategies=[
                HookStrategy.YOU_WONT_BELIEVE,
                HookStrategy.STORY_BASED,
                HookStrategy.CONTRARIAN
            ],
            emotional_triggers=[
                EmotionalTrigger.SURPRISE,
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.SHOCK
            ],
            target_duration_sec=180,
            hook_duration_sec=5,
            pacing="medium",
            preferred_voices=["onyx", "echo"],
            voice_speed=0.95,
            visual_style="cinematic",
            color_palette=["#78350F", "#D97706", "#1F2937"],
            category_id="27",  # Education
            optimal_posting_times=["10:00", "15:00", "20:00"],
            cta_style="subscribe",
            daily_upload_limit=2,
            upload_priority=3,
            title_patterns=[
                "The Untold Story of {topic}",
                "What Really Happened During {topic}",
                "The Dark History of {topic}"
            ],
            thumbnail_styles=["historical_photo", "dramatic", "mystery"]
        )
        
        # FACTS / DID YOU KNOW
        self._configs[NicheType.FACTS_DID_YOU_KNOW] = NicheConfig(
            niche=NicheType.FACTS_DID_YOU_KNOW,
            display_name="Facts & Did You Know",
            description="Mind-blowing facts and interesting trivia",
            primary_sources=["youtube", "reddit", "twitter"],
            secondary_sources=["rss"],
            focus_keywords=[
                "facts", "did you know", "interesting facts", "trivia",
                "amazing facts", "random facts", "science facts"
            ],
            min_sources_to_validate=2,
            virality_threshold=70,
            default_tones=[ContentTone.ENTERTAINING, ContentTone.EDUCATIONAL],
            hook_strategies=[
                HookStrategy.YOU_WONT_BELIEVE,
                HookStrategy.QUESTION_BASED,
                HookStrategy.STATISTIC_SHOCK
            ],
            emotional_triggers=[
                EmotionalTrigger.SURPRISE,
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.JOY
            ],
            target_duration_sec=60,
            hook_duration_sec=2,
            pacing="fast",
            preferred_voices=["alloy", "nova"],
            voice_speed=1.15,
            visual_style="dynamic",
            color_palette=["#F59E0B", "#3B82F6", "#10B981"],
            category_id="27",  # Education
            optimal_posting_times=["08:00", "13:00", "19:00"],
            cta_style="comment",
            daily_upload_limit=6,
            upload_priority=1,
            title_patterns=[
                "{number} Facts That Will Blow Your Mind",
                "Did You Know {topic}?",
                "The Truth About {topic} Nobody Knows"
            ],
            thumbnail_styles=["shock_face", "question_mark", "fact_bubble"]
        )
        
        # HORROR STORIES
        self._configs[NicheType.HORROR_STORIES] = NicheConfig(
            niche=NicheType.HORROR_STORIES,
            display_name="Horror Stories",
            description="Scary stories, true crime, and paranormal content",
            primary_sources=["youtube", "reddit", "twitter"],
            secondary_sources=["telegram"],
            focus_keywords=[
                "horror stories", "true crime", "paranormal", "scary",
                "ghost stories", "creepy", "unsolved mysteries"
            ],
            min_sources_to_validate=2,
            virality_threshold=65,
            default_tones=[ContentTone.DRAMATIC, ContentTone.MYSTERIOUS],
            hook_strategies=[
                HookStrategy.STORY_BASED,
                HookStrategy.PATTERN_INTERRUPT,
                HookStrategy.QUESTION_BASED
            ],
            emotional_triggers=[
                EmotionalTrigger.FEAR,
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.SURPRISE
            ],
            target_duration_sec=180,
            hook_duration_sec=5,
            pacing="slow",
            preferred_voices=["onyx", "echo"],
            voice_speed=0.9,
            visual_style="cinematic",
            color_palette=["#000000", "#DC2626", "#4B5563"],
            category_id="24",  # Entertainment
            optimal_posting_times=["20:00", "22:00", "00:00"],
            cta_style="subscribe",
            daily_upload_limit=2,
            upload_priority=3,
            title_patterns=[
                "The True Story of {topic}",
                "What Happened to {topic} Will Terrify You",
                "The Dark Truth Behind {topic}"
            ],
            thumbnail_styles=["dark_atmosphere", "silhouette", "creepy"]
        )
        
        # RELATIONSHIPS
        self._configs[NicheType.RELATIONSHIPS] = NicheConfig(
            niche=NicheType.RELATIONSHIPS,
            display_name="Relationships & Dating",
            description="Relationship advice, dating tips, and psychology",
            primary_sources=["youtube", "reddit", "twitter"],
            secondary_sources=["rss"],
            focus_keywords=[
                "relationships", "dating advice", "love", "breakup",
                "psychology", "attraction", "communication"
            ],
            min_sources_to_validate=2,
            virality_threshold=65,
            default_tones=[ContentTone.CONVERSATIONAL, ContentTone.EDUCATIONAL],
            hook_strategies=[
                HookStrategy.THIS_IS_WHY,
                HookStrategy.QUESTION_BASED,
                HookStrategy.CONTRARIAN
            ],
            emotional_triggers=[
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.JOY,
                EmotionalTrigger.FEAR
            ],
            target_duration_sec=120,
            hook_duration_sec=4,
            pacing="medium",
            preferred_voices=["nova", "alloy"],
            voice_speed=1.0,
            visual_style="dynamic",
            color_palette=["#EC4899", "#8B5CF6", "#F59E0B"],
            category_id="22",  # People & Blogs
            optimal_posting_times=["11:00", "16:00", "21:00"],
            cta_style="comment",
            daily_upload_limit=4,
            upload_priority=2,
            title_patterns=[
                "Why {topic} Is Ruining Your Relationships",
                "The Psychology Behind {topic}",
                "{number} Signs They're {topic}"
            ],
            thumbnail_styles=["couple", "emotion", "contrast"]
        )
        
        # BUSINESS
        self._configs[NicheType.BUSINESS] = NicheConfig(
            niche=NicheType.BUSINESS,
            display_name="Business & Entrepreneurship",
            description="Business strategies, startup advice, and success stories",
            primary_sources=["youtube", "twitter", "rss"],
            secondary_sources=["reddit", "newsapi"],
            focus_keywords=[
                "business", "entrepreneurship", "startup", "success stories",
                "marketing", "sales", "leadership"
            ],
            min_sources_to_validate=2,
            virality_threshold=65,
            default_tones=[ContentTone.AUTHORITATIVE, ContentTone.INSPIRING],
            hook_strategies=[
                HookStrategy.THIS_IS_WHY,
                HookStrategy.STORY_BASED,
                HookStrategy.STATISTIC_SHOCK
            ],
            emotional_triggers=[
                EmotionalTrigger.INSPIRATION,
                EmotionalTrigger.CURIOSITY,
                EmotionalTrigger.URGENCY
            ],
            target_duration_sec=150,
            hook_duration_sec=4,
            pacing="medium",
            preferred_voices=["onyx", "echo"],
            voice_speed=1.0,
            visual_style="dynamic",
            color_palette=["#1E40AF", "#059669", "#DC2626"],
            category_id="27",  # Education
            optimal_posting_times=["07:00", "12:00", "17:00"],
            cta_style="subscribe",
            daily_upload_limit=3,
            upload_priority=2,
            title_patterns=[
                "How {topic} Built a Billion Dollar Empire",
                "The {topic} Strategy Nobody Talks About",
                "Why Most {topic} Fail (And How to Succeed)"
            ],
            thumbnail_styles=["business_professional", "success", "growth_chart"]
        )
        
        # TRENDING / VIRAL
        self._configs[NicheType.TRENDING_VIRAL] = NicheConfig(
            niche=NicheType.TRENDING_VIRAL,
            display_name="Trending & Viral",
            description="Currently trending topics and viral content",
            primary_sources=["youtube", "twitter", "tiktok"],
            secondary_sources=["reddit", "newsapi", "telegram"],
            focus_keywords=[],  # Dynamic based on trends
            min_sources_to_validate=3,
            virality_threshold=80,
            default_tones=[ContentTone.ENTERTAINING, ContentTone.URGENT],
            hook_strategies=[
                HookStrategy.YOU_WONT_BELIEVE,
                HookStrategy.PATTERN_INTERRUPT,
                HookStrategy.STATISTIC_SHOCK
            ],
            emotional_triggers=[
                EmotionalTrigger.SURPRISE,
                EmotionalTrigger.SHOCK,
                EmotionalTrigger.JOY,
                EmotionalTrigger.CURIOSITY
            ],
            target_duration_sec=60,
            hook_duration_sec=2,
            pacing="fast",
            preferred_voices=["alloy", "nova"],
            voice_speed=1.15,
            visual_style="dynamic",
            color_palette=["#FF0000", "#FFD700", "#000000"],
            category_id="24",  # Entertainment
            optimal_posting_times=["09:00", "14:00", "18:00", "21:00"],
            cta_style="share",
            daily_upload_limit=8,
            upload_priority=1,
            title_patterns=[
                "This {topic} Is Breaking The Internet",
                "You Won't Believe What Happened with {topic}",
                "Everyone Is Talking About {topic}"
            ],
            thumbnail_styles=["viral_moment", "shock_reaction", "trending_badge"]
        )
        
        # CURRENT AFFAIRS (Legacy)
        self._configs[NicheType.CURRENT_AFFAIRS] = NicheConfig(
            niche=NicheType.CURRENT_AFFAIRS,
            display_name="Current Affairs & News",
            description="Breaking news and current events",
            primary_sources=["newsapi", "gnews", "twitter", "youtube"],
            secondary_sources=["reddit", "rss", "telegram"],
            focus_keywords=[
                "breaking news", "politics", "world news", "current events"
            ],
            min_sources_to_validate=3,
            virality_threshold=70,
            default_tones=[ContentTone.URGENT, ContentTone.AUTHORITATIVE],
            hook_strategies=[
                HookStrategy.THIS_IS_WHY,
                HookStrategy.STATISTIC_SHOCK,
                HookStrategy.PATTERN_INTERRUPT
            ],
            emotional_triggers=[
                EmotionalTrigger.URGENCY,
                EmotionalTrigger.FEAR,
                EmotionalTrigger.ANGER
            ],
            target_duration_sec=120,
            hook_duration_sec=4,
            pacing="fast",
            preferred_voices=["onyx", "echo"],
            voice_speed=1.05,
            visual_style="dynamic",
            color_palette=["#DC2626", "#1E40AF", "#1F2937"],
            category_id="25",  # News & Politics
            optimal_posting_times=["07:00", "12:00", "18:00", "22:00"],
            cta_style="subscribe",
            daily_upload_limit=5,
            upload_priority=1,
            title_patterns=[
                "Breaking: {topic}",
                "Why {topic} Matters Now",
                "The Truth About {topic}"
            ],
            thumbnail_styles=["breaking_news", "urgent", "headline"]
        )
    
    def get_config(self, niche: NicheType) -> NicheConfig:
        """Get configuration for a specific niche."""
        return self._configs.get(niche, self._configs[NicheType.TRENDING_VIRAL])
    
    def get_all_niches(self) -> List[Dict]:
        """Get all available niches with basic info."""
        return [
            {
                "id": config.niche.value,
                "name": config.display_name,
                "description": config.description,
                "virality_threshold": config.virality_threshold,
                "daily_limit": config.daily_upload_limit
            }
            for config in self._configs.values()
        ]
    
    def get_niche_by_value(self, niche_value: str) -> Optional[NicheConfig]:
        """Get niche config by string value."""
        try:
            niche_type = NicheType(niche_value)
            return self._configs.get(niche_type)
        except ValueError:
            return None
    
    def get_optimal_voices(self, niche: NicheType) -> List[str]:
        """Get preferred voices for a niche."""
        config = self.get_config(niche)
        return config.preferred_voices
    
    def get_hook_strategies(self, niche: NicheType) -> List[HookStrategy]:
        """Get hook strategies for a niche."""
        config = self.get_config(niche)
        return config.hook_strategies
    
    def get_emotional_triggers(self, niche: NicheType) -> List[EmotionalTrigger]:
        """Get emotional triggers for a niche."""
        config = self.get_config(niche)
        return config.emotional_triggers


# Global instance
niche_config_manager = NicheConfigManager()


def get_niche_config(niche: str) -> NicheConfig:
    """Utility function to get niche configuration."""
    return niche_config_manager.get_niche_by_value(niche)


def get_all_niches() -> List[Dict]:
    """Utility function to get all niches."""
    return niche_config_manager.get_all_niches()
