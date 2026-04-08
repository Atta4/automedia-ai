"""
Algorithm Optimizer

Optimizes content for platform algorithms with:
- CTR-optimized titles
- SEO-optimized descriptions
- Search-optimized tags
- Platform-specific formatting
"""

import random
import re
from datetime import datetime, time
from typing import Dict, List, Optional, Any, Tuple

from config.niche_config import niche_config_manager
from .models import (
    VideoMetadata,
    TitleVariant,
    DescriptionSection,
    SEOScore,
    CTRAnalysis,
    MetadataGenerationRequest,
    PlatformOptimization,
)


class AlgorithmOptimizer:
    """
    Algorithm optimization for viral content.
    
    Features:
    - CTR-optimized title generation
    - SEO-optimized description writing
    - Search-optimized tag generation
    - Platform-specific formatting
    - A/B testing variants
    """
    
    # Power words that increase CTR
    POWER_WORDS = [
        "shocking", "incredible", "unbelievable", "amazing", "mind-blowing",
        "secret", "hidden", "revealed", "exposed", "truth",
        "ultimate", "complete", "essential", "critical", "urgent",
        "proven", "guaranteed", "instant", "effortless", "simple",
        "dangerous", "controversial", "forbidden", "illegal", "banned",
        "free", "bonus", "exclusive", "limited", "rare",
    ]
    
    # Emotional trigger words
    EMOTIONAL_WORDS = {
        "curiosity": ["secret", "hidden", "mystery", "unknown", "revealed"],
        "urgency": ["breaking", "urgent", "now", "alert", "immediate"],
        "fear": ["danger", "warning", "threat", "risk", "crisis"],
        "excitement": ["amazing", "incredible", "awesome", "epic", "legendary"],
        "surprise": ["shocking", "unexpected", "stunning", "jaw-dropping"],
    }
    
    # Platform configurations
    PLATFORM_CONFIGS: Dict[str, PlatformOptimization] = {
        "youtube": PlatformOptimization(
            platform="youtube",
            aspect_ratio="16:9",
            max_duration_sec=7200,
            preferred_resolution="1080p",
            title_max_length=100,
            description_max_length=5000,
            max_tags=500,  # Character limit
            max_hashtags=15,
            subtitle_style="burned_in",
            hook_duration_sec=5,
            cta_placement="end",
        ),
        "youtube_shorts": PlatformOptimization(
            platform="youtube_shorts",
            aspect_ratio="9:16",
            max_duration_sec=60,
            preferred_resolution="1080x1920",
            title_max_length=100,
            description_max_length=5000,
            max_tags=500,
            max_hashtags=15,
            subtitle_style="burned_in",
            hook_duration_sec=2,
            cta_placement="throughout",
        ),
        "instagram_reels": PlatformOptimization(
            platform="instagram_reels",
            aspect_ratio="9:16",
            max_duration_sec=90,
            preferred_resolution="1080x1920",
            title_max_length=2200,
            description_max_length=2200,
            max_tags=30,
            max_hashtags=30,
            subtitle_style="burned_in",
            hook_duration_sec=2,
            cta_placement="end",
        ),
        "tiktok": PlatformOptimization(
            platform="tiktok",
            aspect_ratio="9:16",
            max_duration_sec=180,
            preferred_resolution="1080x1920",
            title_max_length=150,
            description_max_length=2200,
            max_tags=5,
            max_hashtags=5,
            subtitle_style="burned_in",
            hook_duration_sec=1,
            cta_placement="throughout",
        ),
    }
    
    # Title patterns with effectiveness scores
    TITLE_PATTERNS = [
        {
            "pattern": "Why {topic} Is {adjective} Than You Think",
            "style": "curiosity",
            "effectiveness": 85,
        },
        {
            "pattern": "The {superlative} {topic} Secret Nobody Talks About",
            "style": "curiosity",
            "effectiveness": 88,
        },
        {
            "pattern": "{number} {topic} Mistakes You're Making Right Now",
            "style": "list",
            "effectiveness": 82,
        },
        {
            "pattern": "This Is Why Your {topic} Isn't Working",
            "style": "problem",
            "effectiveness": 80,
        },
        {
            "pattern": "What Nobody Tells You About {topic}",
            "style": "curiosity",
            "effectiveness": 86,
        },
        {
            "pattern": "The Truth About {topic} They Don't Want You To Know",
            "style": "conspiracy",
            "effectiveness": 84,
        },
        {
            "pattern": "How {topic} Will Change Everything in {year}",
            "style": "future",
            "effectiveness": 78,
        },
        {
            "pattern": "{topic}: What Just Happened Will Shock You",
            "style": "shock",
            "effectiveness": 87,
        },
        {
            "pattern": "I Tried {topic} for {duration} and This Happened",
            "style": "experiment",
            "effectiveness": 83,
        },
        {
            "pattern": "The {topic} Hack That's Breaking The Internet",
            "style": "viral",
            "effectiveness": 89,
        },
    ]
    
    def __init__(self, openai_client=None, db=None):
        """
        Initialize the algorithm optimizer.
        
        Args:
            openai_client: OpenAI client for AI generation
            db: MongoDB database connection
        """
        self._openai_client = openai_client
        self._db = db
        self._niche_config_manager = niche_config_manager
    
    async def generate_metadata(
        self,
        request: MetadataGenerationRequest
    ) -> VideoMetadata:
        """
        Generate complete optimized metadata.
        
        Args:
            request: Metadata generation request
            
        Returns:
            VideoMetadata with all optimized fields
        """
        # Get niche configuration
        niche_config = self._niche_config_manager.get_niche_by_value(request.niche)
        
        # Generate title variants
        title_variants = await self._generate_title_variants(
            topic=request.topic,
            niche=request.niche,
            niche_config=niche_config,
            exclude_words=request.exclude_words,
        )
        
        # Select best title
        primary_title = self._select_best_title(title_variants)
        
        # Generate description
        description, description_sections = await self._generate_description(
            topic=request.topic,
            niche=request.niche,
            script_content=request.script_content,
            niche_config=niche_config,
        )
        
        # Generate tags
        tags = await self._generate_tags(
            topic=request.topic,
            niche=request.niche,
            niche_config=niche_config,
            required_keywords=request.required_keywords,
        )
        
        # Generate hashtags
        hashtags = self._generate_hashtags(
            topic=request.topic,
            niche=request.niche,
            max_count=self.PLATFORM_CONFIGS.get(request.platform, self.PLATFORM_CONFIGS["youtube"]).max_hashtags,
        )
        
        # Generate thumbnail text
        thumbnail_text = self._generate_thumbnail_text(
            topic=request.topic,
            title=primary_title,
        )
        
        # Generate pinned comment
        pinned_comment = self._generate_pinned_comment(
            topic=request.topic,
            niche=request.niche,
        )
        
        # Generate community post
        community_post = self._generate_community_post(
            topic=request.topic,
            title=primary_title,
            niche=request.niche,
        )
        
        # Get optimal publish time
        optimal_time = self._get_optimal_publish_time(
            niche=request.niche,
            niche_config=niche_config,
        )
        
        # Calculate scores
        seo_score = self._calculate_seo_score(
            title=primary_title,
            description=description,
            tags=tags,
            hashtags=hashtags,
            topic=request.topic,
        )
        
        ctr_score = self._calculate_ctr_score(
            title=primary_title,
            title_variants=title_variants,
        )
        
        # Build metadata
        metadata = VideoMetadata(
            primary_title=primary_title,
            title_variants=title_variants,
            best_title=primary_title,
            description=description,
            description_sections=description_sections,
            tags=tags,
            hashtags=hashtags,
            category_id=niche_config.category_id if niche_config else "25",
            thumbnail_text=thumbnail_text,
            thumbnail_style=niche_config.thumbnail_styles[0] if niche_config and niche_config.thumbnail_styles else "standard",
            pinned_comment=pinned_comment,
            community_post_text=community_post,
            optimal_publish_time=optimal_time,
            seo_score=seo_score.overall,
            ctr_score=ctr_score.ctr_potential,
            niche=request.niche,
            topic=request.topic,
        )
        
        return metadata
    
    async def _generate_title_variants(
        self,
        topic: str,
        niche: str,
        niche_config: Optional[Any],
        exclude_words: List[str]
    ) -> List[TitleVariant]:
        """Generate multiple title variants for A/B testing."""
        variants = []
        
        # Get niche-specific patterns
        if niche_config and niche_config.title_patterns:
            patterns = niche_config.title_patterns
        else:
            patterns = [p["pattern"] for p in self.TITLE_PATTERNS]
        
        # Generate titles from patterns
        fill_values = {
            "topic": topic,
            "adjective": random.choice(["More Important", "More Dangerous", "More Powerful", "Better"]),
            "superlative": random.choice(["Biggest", "Most Important", "Most Dangerous", "Best"]),
            "number": random.choice(["3", "5", "7", "10"]),
            "year": "2025",
            "duration": random.choice(["7 Days", "30 Days", "24 Hours"]),
        }
        
        for pattern in patterns[:8]:  # Limit to 8 variants
            try:
                title = pattern.format(**fill_values)
            except KeyError:
                title = pattern.format(topic=topic)
            
            # Check exclude words
            if any(exclude.lower() in title.lower() for exclude in exclude_words):
                continue
            
            # Limit length
            if len(title) > 100:
                title = title[:97] + "..."
            
            # Determine style
            style = self._detect_title_style(title)
            
            # Calculate CTR score
            ctr_score = self._calculate_title_ctr_score(title)
            
            variants.append(TitleVariant(
                text=title,
                style=style,
                ctr_score=ctr_score,
            ))
        
        # Sort by CTR score
        variants.sort(key=lambda v: v.ctr_score, reverse=True)
        
        return variants
    
    def _detect_title_style(self, title: str) -> str:
        """Detect the style of a title."""
        title_lower = title.lower()
        
        if "?" in title or title_lower.startswith(("why ", "how ", "what ", "when ")):
            return "question"
        if any(word in title_lower for word in self.EMOTIONAL_WORDS["surprise"]):
            return "shock"
        if any(c.isdigit() for c in title):
            return "list"
        if any(word in title_lower for word in self.EMOTIONAL_WORDS["urgency"]):
            return "urgent"
        
        return "curiosity"
    
    def _calculate_title_ctr_score(self, title: str) -> float:
        """Calculate CTR score for a title."""
        score = 50.0  # Base score
        
        # Length bonus (optimal: 40-60 chars)
        length = len(title)
        if 40 <= length <= 60:
            score += 20
        elif 30 <= length <= 70:
            score += 10
        
        # Number bonus
        if any(c.isdigit() for c in title):
            score += 10
        
        # Question bonus
        if title.endswith("?") or title.lower().startswith(("why ", "how ", "what ")):
            score += 8
        
        # Power words bonus
        if any(word in title.lower() for word in self.POWER_WORDS):
            score += 12
        
        # Emotional words bonus
        for emotion_words in self.EMOTIONAL_WORDS.values():
            if any(word in title.lower() for word in emotion_words):
                score += 8
                break
        
        return min(100, score)
    
    def _select_best_title(self, variants: List[TitleVariant]) -> str:
        """Select the best title from variants."""
        if not variants:
            return "Untitled Video"
        
        # Sort by CTR score and return best
        best = max(variants, key=lambda v: v.ctr_score)
        return best.text
    
    async def _generate_description(
        self,
        topic: str,
        niche: str,
        script_content: Optional[str],
        niche_config: Optional[Any]
    ) -> Tuple[str, List[DescriptionSection]]:
        """Generate SEO-optimized description."""
        sections = []
        
        # Hook section (first 2 lines are most important)
        hook = self._generate_description_hook(topic, niche)
        sections.append(DescriptionSection(
            type="hook",
            content=hook,
            order=1,
        ))
        
        # Body section
        body = self._generate_description_body(topic, niche, script_content)
        sections.append(DescriptionSection(
            type="body",
            content=body,
            order=2,
        ))
        
        # CTA section
        cta_style = niche_config.cta_style if niche_config else "subscribe"
        cta = self._generate_description_cta(cta_style)
        sections.append(DescriptionSection(
            type="cta",
            content=cta,
            order=3,
        ))
        
        # Timestamps (if content available)
        if script_content:
            timestamps = self._generate_timestamps(script_content)
            sections.append(DescriptionSection(
                type="timestamps",
                content=timestamps,
                order=4,
            ))
        
        # Hashtags section
        hashtag_section = "\n\n" + " ".join(
            self._generate_hashtags(topic, niche, max_count=5)
        )
        sections.append(DescriptionSection(
            type="hashtags",
            content=hashtag_section,
            order=5,
        ))
        
        # Combine sections
        description = "\n\n".join(s.content for s in sections)
        
        # Limit length
        if len(description) > 5000:
            description = description[:4997] + "..."
        
        return description, sections
    
    def _generate_description_hook(self, topic: str, niche: str) -> str:
        """Generate description hook (first 2 lines)."""
        hooks = [
            f"🔥 Discover the truth about {topic} that will change everything.",
            f"⚡ The {topic} secret nobody talks about - revealed.",
            f"🎯 Everything you need to know about {topic} in one video.",
            f"💡 Why {topic} matters more than you think.",
        ]
        
        return random.choice(hooks)
    
    def _generate_description_body(
        self,
        topic: str,
        niche: str,
        script_content: Optional[str]
    ) -> str:
        """Generate description body."""
        if script_content:
            # Use first 150 words of script
            words = script_content.split()[:150]
            body = " ".join(words)
        else:
            bodies = [
                f"In this video, we dive deep into {topic}. You'll discover insights "
                f"that most people never learn about this subject.",
                f"We're breaking down everything about {topic} - from the basics to "
                f"advanced strategies that actually work.",
                f"Join us as we explore {topic} and uncover the truth behind the hype.",
            ]
            body = random.choice(bodies)
        
        return body
    
    def _generate_description_cta(self, cta_style: str) -> str:
        """Generate description CTA."""
        ctas = {
            "subscribe": "🔔 Subscribe and hit the bell for more viral content!",
            "comment": "💬 Drop your thoughts in the comments below!",
            "like": "👍 Smash that like button if this helped!",
            "share": "📢 Share this with someone who needs to see it!",
        }
        
        return ctas.get(cta_style, ctas["subscribe"])
    
    def _generate_timestamps(self, script_content: str) -> str:
        """Generate timestamps from script content."""
        # Simple timestamp generation
        # In production, would parse script segments
        timestamps = [
            "0:00 - Intro",
            "0:15 - Main Content",
            "1:00 - Key Insights",
            "1:45 - Conclusion",
        ]
        
        return "\n".join(timestamps)
    
    async def _generate_tags(
        self,
        topic: str,
        niche: str,
        niche_config: Optional[Any],
        required_keywords: Optional[List[str]]
    ) -> List[str]:
        """Generate search-optimized tags."""
        tags = []
        
        # Niche tags
        niche_clean = niche.replace("_", "")
        tags.extend([
            niche_clean,
            f"{niche}content",
            f"{niche}videos",
            f"{niche.replace('_', ' ')}",
        ])
        
        # Topic-based tags
        topic_words = topic.lower().split()
        significant_words = [
            w for w in topic_words
            if len(w) > 3 and w not in {"this", "that", "with", "from", "have", "will", "about"}
        ]
        tags.extend(significant_words[:5])
        
        # Full topic as tag
        tags.append(topic.lower())
        
        # Required keywords
        if required_keywords:
            tags.extend(required_keywords[:5])
        
        # Viral/trending tags
        tags.extend(["viral", "trending", "fyp"])
        
        # Remove duplicates and limit
        tags = list(dict.fromkeys(tags))  # Preserve order, remove duplicates
        
        return tags[:25]  # YouTube allows up to 500 characters
    
    def _generate_hashtags(
        self,
        topic: str,
        niche: str,
        max_count: int = 15
    ) -> List[str]:
        """Generate hashtags."""
        hashtags = []
        
        # Niche hashtag
        hashtags.append(f"#{niche.replace('_', '')}")
        
        # Topic hashtag (simplified)
        topic_tag = "".join(word.capitalize() for word in topic.split()[:3])
        hashtags.append(f"#{topic_tag}")
        
        # General viral hashtags
        hashtags.extend([
            "#viral",
            "#trending",
            "#fyp",
            f"#{niche.replace('_', '')}videos",
        ])
        
        return hashtags[:max_count]
    
    def _generate_thumbnail_text(
        self,
        topic: str,
        title: str
    ) -> str:
        """Generate short thumbnail text."""
        # Extract key words from title
        words = title.split()
        
        # Find most impactful short phrase
        if len(words) <= 4:
            return title
        
        # Try to get 3-4 word phrase
        if "Why" in title:
            idx = title.find("Why")
            phrase = title[idx:idx+30]
        elif "The" in title:
            idx = title.find("The")
            phrase = title[idx:idx+30]
        else:
            phrase = " ".join(words[:4])
        
        # Ensure it's short enough
        if len(phrase) > 30:
            phrase = phrase[:27] + "..."
        
        return phrase
    
    def _generate_pinned_comment(
        self,
        topic: str,
        niche: str
    ) -> str:
        """Generate pinned comment."""
        comments = [
            f"What's your take on {topic}? Let me know in the replies! 👇",
            f"Drop a 🔥 if this video helped you understand {topic} better!",
            f"Question for you: What's your experience with {topic}? Comment below!",
        ]
        
        return random.choice(comments)
    
    def _generate_community_post(
        self,
        topic: str,
        title: str,
        niche: str
    ) -> str:
        """Generate community post text."""
        posts = [
            f"🎬 NEW VIDEO: {title}\n\n"
            f"We're diving deep into {topic}. You don't want to miss this one!\n\n"
            f"Watch now and let me know your thoughts! 👇",
            
            f"📢 Just dropped: {title}\n\n"
            f"This one about {topic} is special. Check it out and subscribe for more!",
            
            f"🔥 {title}\n\n"
            f"If you're interested in {topic}, this video is for you. Link in bio!",
        ]
        
        return random.choice(posts)
    
    def _get_optimal_publish_time(
        self,
        niche: str,
        niche_config: Optional[Any]
    ) -> str:
        """Get optimal publish time."""
        if niche_config and niche_config.optimal_posting_times:
            return random.choice(niche_config.optimal_posting_times)
        
        # Default optimal times by niche type
        default_times = {
            "motivation": "06:00",
            "finance": "07:00",
            "ai_tech": "09:00",
            "health_fitness": "06:00",
            "entertainment": "18:00",
        }
        
        return default_times.get(niche, "18:00")
    
    def _calculate_seo_score(
        self,
        title: str,
        description: str,
        tags: List[str],
        hashtags: List[str],
        topic: str
    ) -> SEOScore:
        """Calculate overall SEO score."""
        # Title score
        title_score = self._calculate_title_ctr_score(title)
        
        # Description score
        desc_score = 50.0
        if len(description) >= 200:
            desc_score += 20
        if len(description) >= 500:
            desc_score += 10
        if "subscribe" in description.lower() or "comment" in description.lower():
            desc_score += 10
        if ":" in description:  # Likely has timestamps
            desc_score += 10
        
        # Tags score
        tags_score = min(100, len(tags) * 5)
        
        # Hashtag score
        hashtag_score = min(100, len(hashtags) * 10)
        
        # Overall score (weighted average)
        overall = (
            title_score * 0.35 +
            desc_score * 0.30 +
            tags_score * 0.20 +
            hashtag_score * 0.15
        )
        
        # Generate recommendations
        recommendations = []
        if len(title) < 40:
            recommendations.append("Consider longer, more descriptive titles")
        if len(description) < 200:
            recommendations.append("Add more detailed description")
        if len(tags) < 10:
            recommendations.append("Add more relevant tags")
        if len(hashtags) < 5:
            recommendations.append("Add more hashtags")
        
        return SEOScore(
            overall=overall,
            title_score=title_score,
            description_score=desc_score,
            tags_score=tags_score,
            hashtag_score=hashtag_score,
            keyword_density=70.0,  # Simplified
            has_timestamps=":" in description,
            has_cta="subscribe" in description.lower() or "comment" in description.lower(),
            has_links="http" in description.lower(),
            recommendations=recommendations,
        )
    
    def _calculate_ctr_score(
        self,
        title: str,
        title_variants: List[TitleVariant]
    ) -> CTRAnalysis:
        """Calculate CTR potential score."""
        # Analyze title
        has_numbers = any(c.isdigit() for c in title)
        has_question = title.endswith("?")
        has_power_words = any(word in title.lower() for word in self.POWER_WORDS)
        
        # Calculate emotional score
        emotional_score = 0
        for emotion_words in self.EMOTIONAL_WORDS.values():
            if any(word in title.lower() for word in emotion_words):
                emotional_score = 50
                break
        emotional_score += min(50, sum(1 for w in title.split() if w.lower() in self.POWER_WORDS) * 10)
        
        # Overall CTR potential
        ctr_potential = 50.0
        if 40 <= len(title) <= 60:
            ctr_potential += 20
        if has_numbers:
            ctr_potential += 10
        if has_question:
            ctr_potential += 8
        if has_power_words:
            ctr_potential += 12
        
        # Generate recommendations
        recommendations = []
        if len(title) < 40:
            recommendations.append("Title may be too short for optimal CTR")
        if not has_numbers:
            recommendations.append("Consider adding numbers for higher CTR")
        if not has_power_words:
            recommendations.append("Add power words to increase emotional impact")
        
        return CTRAnalysis(
            ctr_potential=min(100, ctr_potential),
            title_length_optimal=40 <= len(title) <= 60,
            title_has_numbers=has_numbers,
            title_has_question=has_question,
            title_has_power_words=has_power_words,
            title_emotional_score=emotional_score,
            thumbnail_text_present=True,
            thumbnail_contrast_score=75.0,
            thumbnail_face_present=False,
            recommendations=recommendations,
        )
    
    def get_platform_config(self, platform: str) -> PlatformOptimization:
        """Get platform-specific configuration."""
        return self.PLATFORM_CONFIGS.get(platform, self.PLATFORM_CONFIGS["youtube"])
    
    def optimize_for_platform(
        self,
        metadata: VideoMetadata,
        platform: str
    ) -> VideoMetadata:
        """Optimize existing metadata for a specific platform."""
        config = self.get_platform_config(platform)
        
        # Adjust title length
        if len(metadata.primary_title) > config.title_max_length:
            metadata.primary_title = metadata.primary_title[:config.title_max_length - 3] + "..."
        
        # Adjust description length
        if len(metadata.description) > config.description_max_length:
            metadata.description = metadata.description[:config.description_max_length - 3] + "..."
        
        # Adjust tags
        if len(metadata.tags) > config.max_tags:
            metadata.tags = metadata.tags[:config.max_tags]
        
        # Adjust hashtags
        if len(metadata.hashtags) > config.max_hashtags:
            metadata.hashtags = metadata.hashtags[:config.max_hashtags]
        
        return metadata
