"""
Viral Script Generator

Generates high-retention, viral-optimized scripts using proven frameworks.
"""

import random
from datetime import datetime
from typing import Dict, List, Optional, Any

from config.niche_config import niche_config_manager, ContentTone
from .models import (
    ViralScript,
    ScriptSegment,
    ScriptSegmentType,
    HookFramework,
    ScriptGenerationRequest,
    ScriptQualityMetrics,
    RetentionAnalysis,
)
from .hook_library import HookLibrary


class ViralScriptGenerator:
    """
    Viral script generator using proven frameworks.
    
    Features:
    - Hook-based opening (first 3 seconds)
    - Open loops for curiosity
    - Fast pacing with no fluff
    - Emotional triggers throughout
    - Retention hooks every 5-8 seconds
    - Strong ending with twist/CTA
    """
    
    # Segment duration guidelines (in seconds)
    SEGMENT_DURATIONS = {
        ScriptSegmentType.HOOK: (2.5, 4),
        ScriptSegmentType.OPEN_LOOP: (3, 5),
        ScriptSegmentType.CONTEXT: (10, 15),
        ScriptSegmentType.CONTENT: (15, 25),
        ScriptSegmentType.RETENTION_HOOK: (3, 5),
        ScriptSegmentType.TRANSITION: (2, 4),
        ScriptSegmentType.CLIMAX: (10, 15),
        ScriptSegmentType.CTA: (5, 8),
        ScriptSegmentType.TWIST: (5, 8),
    }
    
    # Pacing by niche
    PACING_SPEEDS = {
        "fast": 160,  # Words per minute
        "medium": 140,
        "slow": 120,
    }
    
    def __init__(self, openai_client=None, db=None):
        """
        Initialize the viral script generator.
        
        Args:
            openai_client: OpenAI client for AI generation
            db: MongoDB database connection
        """
        self._openai_client = openai_client
        self._db = db
        self._niche_config_manager = niche_config_manager
        self._hook_library = HookLibrary()
    
    async def generate_script(
        self,
        request: ScriptGenerationRequest
    ) -> ViralScript:
        """
        Generate a viral-optimized script.
        
        Args:
            request: Script generation request
            
        Returns:
            ViralScript with complete structure
        """
        # Get niche configuration
        niche_config = niche_config_manager.get_niche_by_value(request.niche)
        
        # Determine hook framework
        hook_framework = request.hook_framework
        if not hook_framework:
            hook_framework = self._hook_library.get_best_framework_for_niche(
                request.niche,
                request.topic
            )
        
        # Generate hook
        variation_seed = request.variation_seed or random.randint(0, 10000)
        hook_text = self._hook_library.get_hook(
            hook_framework,
            request.topic,
            variation_seed
        )
        
        # Generate script structure
        segments = await self._generate_script_structure(
            request=request,
            hook_framework=hook_framework,
            niche_config=niche_config,
        )
        
        # Build full text
        full_text = " ".join(s.text for s in segments)
        
        # Generate title (CTR optimized)
        title = await self._generate_title(
            topic=request.topic,
            niche=request.niche,
            hook_framework=hook_framework,
        )
        
        # Generate description and tags
        description, tags, hashtags = await self._generate_metadata(
            topic=request.topic,
            niche=request.niche,
            full_text=full_text,
        )
        
        # Generate CTA
        cta_text, cta_type = self._generate_cta(
            niche=request.niche,
            niche_config=niche_config,
        )
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(segments, full_text)
        
        # Build script
        script = ViralScript(
            niche=request.niche,
            topic=request.topic,
            title=title,
            hook_framework=hook_framework,
            hook_text=hook_text,
            segments=segments,
            full_text=full_text,
            estimated_duration_sec=quality_metrics.estimated_duration_sec,
            word_count=quality_metrics.word_count,
            retention_score=quality_metrics.retention_potential,
            pacing_score=quality_metrics.pacing_quality,
            emotional_arc_score=quality_metrics.emotional_impact,
            description=description,
            tags=tags,
            hashtags=hashtags,
            cta_text=cta_text,
            cta_type=cta_type,
            variation_seed=variation_seed,
            creativity_factor=request.creativity_factor,
            metadata={
                "quality_metrics": quality_metrics.model_dump(),
                "niche_config": niche_config.display_name if niche_config else None,
            }
        )
        
        return script
    
    async def _generate_script_structure(
        self,
        request: ScriptGenerationRequest,
        hook_framework: HookFramework,
        niche_config: Optional[Any]
    ) -> List[ScriptSegment]:
        """Generate the complete script structure with segments."""
        
        segments = []
        order = 0
        
        # Get pacing info
        pacing = niche_config.pacing if niche_config else "fast"
        words_per_minute = self.PACING_SPEEDS.get(pacing, 150)
        
        # Calculate target word count based on duration
        target_words = int((request.target_duration_sec / 60) * words_per_minute)
        
        # 1. HOOK (First 3 seconds - pattern interrupt)
        order += 1
        hook_duration = self._hook_library.get_hook_duration(hook_framework)
        hook_words = int((hook_duration[0] / 60) * words_per_minute)
        
        hook_text = self._generate_hook_content(
            framework=hook_framework,
            topic=request.topic,
            word_target=hook_words,
            seed=request.variation_seed,
        )
        
        segments.append(ScriptSegment(
            type=ScriptSegmentType.HOOK,
            order=order,
            text=hook_text,
            duration_estimate_sec=hook_duration[0],
            visual_cue="Dramatic opening visual",
            emphasis="strong",
            has_pattern_interrupt=True,
        ))
        
        # 2. OPEN LOOP (Create curiosity)
        order += 1
        open_loop_words = int((4 / 60) * words_per_minute)
        
        open_loop_text = self._generate_open_loop(
            topic=request.topic,
            hook_framework=hook_framework,
            word_target=open_loop_words,
            seed=request.variation_seed,
        )
        
        segments.append(ScriptSegment(
            type=ScriptSegmentType.OPEN_LOOP,
            order=order,
            text=open_loop_text,
            duration_estimate_sec=4,
            visual_cue="Intriguing visual tease",
            has_open_loop=True,
        ))
        
        # 3. CONTEXT (Background setup)
        order += 1
        context_words = int((12 / 60) * words_per_minute)
        
        context_text = await self._generate_context(
            topic=request.topic,
            niche=request.niche,
            reference=request.reference_material,
            word_target=context_words,
            creativity=request.creativity_factor,
        )
        
        segments.append(ScriptSegment(
            type=ScriptSegmentType.CONTEXT,
            order=order,
            text=context_text,
            duration_estimate_sec=12,
            visual_cue="Context-setting visuals",
        ))
        
        # 4. CONTENT BLOCKS with retention hooks
        # Divide remaining time into content blocks with retention hooks
        remaining_words = target_words - hook_words - open_loop_words - context_words - 30  # Reserve for CTA/twist
        content_blocks = 3
        
        for block in range(content_blocks):
            # Retention hook before each content block
            order += 1
            retention_words = int((4 / 60) * words_per_minute)
            
            retention_text = self._generate_retention_hook(
                topic=request.topic,
                block_number=block + 1,
                total_blocks=content_blocks,
                word_target=retention_words,
                emotional_trigger=niche_config.emotional_triggers[0] if niche_config and niche_config.emotional_triggers else None,
            )
            
            segments.append(ScriptSegment(
                type=ScriptSegmentType.RETENTION_HOOK,
                order=order,
                text=retention_text,
                duration_estimate_sec=4,
                visual_cue="Pattern interrupt visual",
                has_pattern_interrupt=True,
            ))
            
            # Content block
            order += 1
            block_words = int((remaining_words / content_blocks / 60) * words_per_minute)
            
            content_text = await self._generate_content_block(
                topic=request.topic,
                niche=request.niche,
                block_number=block + 1,
                reference=request.reference_material,
                word_target=block_words,
                creativity=request.creativity_factor,
            )
            
            segments.append(ScriptSegment(
                type=ScriptSegmentType.CONTENT,
                order=order,
                text=content_text,
                duration_estimate_sec=15,
                visual_cue=f"Content visual {block + 1}",
            ))
        
        # 5. CLIMAX (Main revelation/payoff)
        order += 1
        climax_words = int((12 / 60) * words_per_minute)
        
        climax_text = await self._generate_climax(
            topic=request.topic,
            niche=request.niche,
            hook_framework=hook_framework,
            word_target=climax_words,
            creativity=request.creativity_factor,
        )
        
        segments.append(ScriptSegment(
            type=ScriptSegmentType.CLIMAX,
            order=order,
            text=climax_text,
            duration_estimate_sec=12,
            visual_cue="Dramatic climax visual",
            emphasis="strong",
        ))
        
        # 6. TWIST (Optional, for extra retention)
        if request.creativity_factor > 0.5:
            order += 1
            twist_words = int((5 / 60) * words_per_minute)
            
            twist_text = self._generate_twist(
                topic=request.topic,
                word_target=twist_words,
                seed=request.variation_seed,
            )
            
            segments.append(ScriptSegment(
                type=ScriptSegmentType.TWIST,
                order=order,
                text=twist_text,
                duration_estimate_sec=5,
                visual_cue="Surprise visual",
            ))
        
        # 7. CTA (Call to action)
        order += 1
        cta_words = int((6 / 60) * words_per_minute)
        
        cta_text = self._generate_cta_content(
            niche=request.niche,
            topic=request.topic,
            word_target=cta_words,
        )
        
        segments.append(ScriptSegment(
            type=ScriptSegmentType.CTA,
            order=order,
            text=cta_text,
            duration_estimate_sec=6,
            visual_cue="CTA overlay",
        ))
        
        return segments
    
    def _generate_hook_content(
        self,
        framework: HookFramework,
        topic: str,
        word_target: int,
        seed: Optional[int] = None
    ) -> str:
        """Generate hook content using the hook library."""
        return self._hook_library.get_hook(framework, topic, seed)
    
    def _generate_open_loop(
        self,
        topic: str,
        hook_framework: HookFramework,
        word_target: int,
        seed: Optional[int]
    ) -> str:
        """Generate open loop that creates curiosity."""
        templates = [
            "But here's what makes this different from anything you've seen before...",
            "And what happened next? Nobody saw it coming.",
            "But there's a twist to this story that changes everything.",
            "What I'm about to reveal will completely shift your perspective.",
            "But first, you need to understand the one thing nobody talks about.",
        ]
        
        random.seed(seed)
        return random.choice(templates)
    
    async def _generate_context(
        self,
        topic: str,
        niche: str,
        reference: Optional[str],
        word_target: int,
        creativity: float
    ) -> str:
        """Generate context/background segment."""
        # In production, this would use AI to generate context
        # For now, use template-based generation
        
        templates = [
            f"To understand {topic}, we need to go back to where it all started.",
            f"Let me break down exactly what's happening with {topic}.",
            f"Here's the background you need to know about {topic}.",
            f"The story of {topic} is more complex than you might think.",
        ]
        
        return random.choice(templates)
    
    def _generate_retention_hook(
        self,
        topic: str,
        block_number: int,
        total_blocks: int,
        word_target: int,
        emotional_trigger: Optional[str] = None
    ) -> str:
        """Generate retention hook to keep viewers watching."""
        templates = [
            "But wait until you hear what comes next.",
            "This is where it gets really interesting.",
            "And this is only part one of what I discovered.",
            "But here's the part that will blow your mind.",
            "What happened next changed everything.",
        ]
        
        return random.choice(templates)
    
    async def _generate_content_block(
        self,
        topic: str,
        niche: str,
        block_number: int,
        reference: Optional[str],
        word_target: int,
        creativity: float
    ) -> str:
        """Generate main content block."""
        # In production, use AI with reference material
        templates = [
            f"Let's dive deeper into {topic}.",
            f"Here's what you need to know about {topic}.",
            f"The key insight about {topic} is this.",
        ]
        
        return random.choice(templates)
    
    async def _generate_climax(
        self,
        topic: str,
        niche: str,
        hook_framework: HookFramework,
        word_target: int,
        creativity: float
    ) -> str:
        """Generate climax/main revelation."""
        templates = [
            f"And that's the truth about {topic} that changes everything.",
            f"This is why {topic} matters more than you ever realized.",
            f"The real story of {topic} is finally clear.",
        ]
        
        return random.choice(templates)
    
    def _generate_twist(
        self,
        topic: str,
        word_target: int,
        seed: Optional[int]
    ) -> str:
        """Generate twist ending."""
        templates = [
            "But there's one more thing you need to know...",
            "Here's the plot twist nobody expected.",
            "And just when you thought it was over, this happened.",
        ]
        
        random.seed(seed)
        return random.choice(templates)
    
    def _generate_cta_content(
        self,
        niche: str,
        topic: str,
        word_target: int
    ) -> str:
        """Generate CTA content."""
        templates = [
            "If this opened your eyes, hit that like button and subscribe for more.",
            "Drop a comment below telling me what you think about this.",
            "Share this with someone who needs to hear it.",
            "Subscribe and turn on notifications so you never miss an update.",
        ]
        
        return random.choice(templates)
    
    async def _generate_title(
        self,
        topic: str,
        niche: str,
        hook_framework: HookFramework
    ) -> str:
        """Generate CTR-optimized title."""
        # Get title patterns from niche config
        config = niche_config_manager.get_niche_by_value(niche)
        
        if config and config.title_patterns:
            patterns = config.title_patterns
        else:
            patterns = [
                "Why {topic} Is Changing Everything",
                "The Truth About {topic}",
                "What Nobody Tells You About {topic}",
                "This {topic} Secret Will Shock You",
                "How {topic} Will Impact Your Life",
            ]
        
        # Select pattern based on hook framework
        title = random.choice(patterns).format(topic=topic, year="2025", number="3", amount="10K")
        
        # Ensure title is under 60 characters for optimal CTR
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title
    
    async def _generate_metadata(
        self,
        topic: str,
        niche: str,
        full_text: str
    ) -> tuple:
        """Generate description, tags, and hashtags."""
        # Generate tags from topic
        tags = [
            niche.replace("_", ""),
            niche.replace("_", " "),
            topic.lower()[:30],
            "viral",
            "trending",
        ]
        
        # Generate hashtags
        hashtags = [
            f"#{niche.replace('_', '')}",
            "#viral",
            "#trending",
            "#fyp",
        ]
        
        # Generate description
        description = f"Discover the truth about {topic}. This video reveals everything you need to know.\n\n"
        description += "🔔 Subscribe for more viral content!\n\n"
        description += f"Tags: {', '.join(tags)}"
        
        return description, tags, hashtags
    
    def _generate_cta(
        self,
        niche: str,
        niche_config: Optional[Any]
    ) -> tuple:
        """Generate CTA text and type."""
        cta_style = niche_config.cta_style if niche_config else "subscribe"
        
        cta_map = {
            "subscribe": ("Subscribe and hit the bell for more!", "subscribe"),
            "comment": ("Drop your thoughts in the comments below!", "comment"),
            "like": ("Smash that like button if this helped!", "like"),
            "share": ("Share this with someone who needs to see it!", "share"),
        }
        
        return cta_map.get(cta_style, cta_map["subscribe"])
    
    def _calculate_quality_metrics(
        self,
        segments: List[ScriptSegment],
        full_text: str
    ) -> ScriptQualityMetrics:
        """Calculate quality metrics for the generated script."""
        word_count = len(full_text.split())
        estimated_duration = (word_count / 150) * 60  # 150 WPM average
        
        # Count pattern interrupts and open loops
        pattern_interrupts = sum(1 for s in segments if s.has_pattern_interrupt)
        open_loops = sum(1 for s in segments if s.has_open_loop)
        
        # Calculate scores
        retention_score = min(100, 60 + (pattern_interrupts * 10) + (open_loops * 10))
        pacing_score = min(100, 70 + (len(segments) * 2))
        emotional_impact = 75  # Base score, would be AI-analyzed in production
        
        # Generate strengths and improvements
        strengths = []
        improvements = []
        
        if pattern_interrupts >= 3:
            strengths.append("Strong pattern interrupts throughout")
        elif pattern_interrupts < 2:
            improvements.append("Add more pattern interrupts")
        
        if open_loops >= 1:
            strengths.append("Effective curiosity building")
        
        if len(segments) >= 7:
            strengths.append("Good segment variety")
        
        if word_count < 100:
            improvements.append("Consider expanding content")
        elif word_count > 300:
            improvements.append("Consider trimming for better retention")
        
        return ScriptQualityMetrics(
            overall_quality=(retention_score + pacing_score + emotional_impact) / 3,
            hook_strength=85,
            retention_potential=retention_score,
            pacing_quality=pacing_score,
            emotional_impact=emotional_impact,
            clarity_score=80,
            word_count=word_count,
            estimated_duration_sec=estimated_duration,
            segment_count=len(segments),
            pattern_interrupt_count=pattern_interrupts,
            open_loop_count=open_loops,
            strengths=strengths,
            improvements=improvements,
        )
    
    def analyze_retention(self, script: ViralScript) -> RetentionAnalysis:
        """Analyze retention potential of a script."""
        # Count retention elements
        pattern_interrupts = sum(1 for s in script.segments if s.has_pattern_interrupt)
        open_loops = sum(1 for s in script.segments if s.has_open_loop)
        
        # Calculate average sentence length
        sentences = script.full_text.replace("!", ".").replace("?", ".").split(".")
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # Calculate retention score
        retention_score = min(100, 50 + (pattern_interrupts * 12) + (open_loops * 10))
        
        # Identify risk points (long segments without hooks)
        risk_points = []
        for i, segment in enumerate(script.segments):
            if segment.duration_estimate_sec > 20 and not segment.has_pattern_interrupt:
                risk_points.append({
                    "segment": i,
                    "type": segment.type.value,
                    "duration": segment.duration_estimate_sec,
                    "reason": "Long segment without pattern interrupt",
                })
        
        # Generate recommendations
        recommendations = []
        if pattern_interrupts < 3:
            recommendations.append("Add more pattern interrupts")
        if open_loops < 1:
            recommendations.append("Add curiosity-building open loops")
        if avg_sentence_length > 20:
            recommendations.append("Use shorter sentences for better pacing")
        if risk_points:
            recommendations.append("Break up long segments")
        
        return RetentionAnalysis(
            retention_score=retention_score,
            hook_effectiveness=85,
            hook_type=script.hook_framework.value,
            retention_hooks=[
                {"segment": s.order, "type": s.type.value}
                for s in script.segments if s.type == ScriptSegmentType.RETENTION_HOOK
            ],
            retention_hook_interval_sec=script.estimated_duration_sec / max(1, len([
                s for s in script.segments if s.type == ScriptSegmentType.RETENTION_HOOK
            ])),
            avg_sentence_length=avg_sentence_length,
            pacing_variety=75,
            has_pattern_interrupts=pattern_interrupts > 0,
            pattern_interrupt_count=pattern_interrupts,
            risk_points=risk_points,
            recommendations=recommendations,
        )
