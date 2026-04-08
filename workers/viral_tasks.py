"""
Celery Tasks for Multi-Niche Viral Content Engine

Refactored tasks to support the new multi-niche architecture with:
- Niche-aware topic discovery
- Viral script generation
- Algorithm-optimized metadata
- Smart upload scheduling
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio

from celery import Celery
from celery.exceptions import Retry

# Import new modules
from config.niche_config import niche_config_manager, get_niche_config
from modules.niche_manager import NicheManager
from modules.smart_discovery import SmartTopicDiscoveryEngine, TopicGenerationRequest
from modules.viral_script_generator import ViralScriptGenerator, ScriptGenerationRequest
from modules.algorithm_optimizer import AlgorithmOptimizer, MetadataGenerationRequest
from modules.content_variation import ContentVariationEngine, VariationRequest
from modules.upload_optimizer import UploadStrategyOptimizer, UploadPriority

# Initialize Celery
celery_app = Celery(
    'automedia_viral',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=1,
)

# Global instances (initialized on first use)
_niche_manager: Optional[NicheManager] = None
_discovery_engine: Optional[SmartTopicDiscoveryEngine] = None
_script_generator: Optional[ViralScriptGenerator] = None
_metadata_optimizer: Optional[AlgorithmOptimizer] = None
_variation_engine: Optional[ContentVariationEngine] = None
_upload_optimizer: Optional[UploadStrategyOptimizer] = None


def get_db():
    """Get MongoDB database connection."""
    from core.database import get_database
    return asyncio.run(get_database())


def get_openai_client():
    """Get OpenAI client."""
    from config.settings import get_settings
    from openai import AsyncOpenAI
    
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ============================================================================
# TOPIC DISCOVERY TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=3)
def discover_viral_topics(
    self,
    niche: str,
    region: str = "US",
    language: str = "en",
    max_topics: int = 10,
    min_virality_score: int = 60,
) -> Dict[str, Any]:
    """
    Discover viral topics for a specific niche.
    
    Args:
        niche: Target niche (e.g., "motivation", "finance", "ai_tech")
        region: Geographic region for trends
        language: Content language
        max_topics: Maximum topics to discover
        min_virality_score: Minimum virality score threshold
        
    Returns:
        Dict with discovered topics and metadata
    """
    try:
        # Validate niche
        if not niche_config_manager.get_niche_by_value(niche):
            return {
                "success": False,
                "error": f"Unknown niche: {niche}",
                "available_niches": [n["id"] for n in niche_config_manager.get_all_niches()],
            }
        
        # Initialize engine
        global _discovery_engine
        if _discovery_engine is None:
            _discovery_engine = SmartTopicDiscoveryEngine(db=get_db())
        
        # Create request
        request = TopicGenerationRequest(
            niche=niche,
            region=region,
            language=language,
            max_topics=max_topics,
            min_virality_score=min_virality_score,
        )
        
        # Run discovery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_discovery_engine.discover_topics(request))
        finally:
            loop.close()
        
        # Convert to serializable format
        topics = []
        for topic in result.topics:
            topics.append({
                "niche": topic.niche,
                "topic": topic.topic,
                "normalized_keyword": topic.normalized_keyword,
                "virality_score": topic.virality_score.overall,
                "virality_breakdown": {
                    "trend": topic.virality_score.trend_score,
                    "emotional": topic.virality_score.emotional_score,
                    "ctr": topic.virality_score.ctr_potential,
                    "engagement": topic.virality_score.engagement_potential,
                    "novelty": topic.virality_score.novelty_score,
                },
                "reason": topic.virality_score.reason,
                "emotional_triggers": topic.emotional_triggers,
                "ctr_patterns": topic.ctr_patterns,
                "is_validated": topic.is_validated,
                "validation_reason": topic.validation_reason,
                "tags": topic.tags,
            })
        
        return {
            "success": True,
            "niche": niche,
            "topics": topics,
            "total_discovered": result.total_discovered,
            "total_validated": result.total_validated,
            "avg_virality_score": result.avg_virality_score,
            "discovery_duration_sec": result.discovery_duration_sec,
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def score_topic_virality(
    self,
    niche: str,
    topic: str,
) -> Dict[str, Any]:
    """
    Calculate virality score for a specific topic.
    
    Args:
        niche: Content niche
        topic: Topic title/text
        
    Returns:
        Dict with virality score breakdown
    """
    try:
        global _discovery_engine
        if _discovery_engine is None:
            _discovery_engine = SmartTopicDiscoveryEngine(db=get_db())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _discovery_engine.discover_single_topic(niche, topic)
            )
        finally:
            loop.close()
        
        if not result:
            return {
                "success": False,
                "error": "Could not score topic",
            }
        
        return {
            "success": True,
            "topic": topic,
            "niche": niche,
            "virality_score": result.virality_score.overall,
            "breakdown": _discovery_engine.get_virality_breakdown(result),
            "emotional_triggers": result.emotional_triggers,
            "ctr_patterns": result.ctr_patterns,
            "recommendation": "High potential - proceed with script generation" 
                              if result.virality_score.overall >= 70 
                              else "Moderate potential - consider optimization",
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


# ============================================================================
# SCRIPT GENERATION TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=2)
def generate_viral_script(
    self,
    niche: str,
    topic: str,
    topic_keyword: Optional[str] = None,
    target_duration_sec: int = 90,
    creativity_factor: float = 0.7,
    hook_framework: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a viral-optimized script for a topic.
    
    Args:
        niche: Content niche
        topic: Topic title
        topic_keyword: Optional normalized keyword
        target_duration_sec: Target video duration
        creativity_factor: Creativity level (0.0-1.0)
        hook_framework: Optional specific hook framework to use
        
    Returns:
        Dict with generated script and metadata
    """
    try:
        # Validate niche
        config = niche_config_manager.get_niche_by_value(niche)
        if not config:
            return {
                "success": False,
                "error": f"Unknown niche: {niche}",
            }
        
        # Initialize generator
        global _script_generator
        if _script_generator is None:
            _script_generator = ViralScriptGenerator(
                openai_client=get_openai_client(),
                db=get_db()
            )
        
        # Create request
        request = ScriptGenerationRequest(
            niche=niche,
            topic=topic,
            topic_keyword=topic_keyword,
            target_duration_sec=target_duration_sec,
            creativity_factor=creativity_factor,
            hook_framework=hook_framework,
        )
        
        # Generate script
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            script = loop.run_until_complete(_script_generator.generate_script(request))
        finally:
            loop.close()
        
        # Convert to serializable format
        segments = []
        for seg in script.segments:
            segments.append({
                "type": seg.type.value,
                "order": seg.order,
                "text": seg.text,
                "duration_estimate_sec": seg.duration_estimate_sec,
                "visual_cue": seg.visual_cue,
                "has_pattern_interrupt": seg.has_pattern_interrupt,
                "has_open_loop": seg.has_open_loop,
            })
        
        # Analyze retention
        retention_analysis = _script_generator.analyze_retention(script)
        
        return {
            "success": True,
            "script": {
                "niche": script.niche,
                "topic": script.topic,
                "title": script.title,
                "hook_framework": script.hook_framework.value,
                "hook_text": script.hook_text,
                "segments": segments,
                "full_text": script.full_text,
                "estimated_duration_sec": script.estimated_duration_sec,
                "word_count": script.word_count,
                "retention_score": script.retention_score,
                "pacing_score": script.pacing_score,
                "description": script.description,
                "tags": script.tags,
                "hashtags": script.hashtags,
                "cta_text": script.cta_text,
                "cta_type": script.cta_type,
            },
            "retention_analysis": {
                "retention_score": retention_analysis.retention_score,
                "hook_effectiveness": retention_analysis.hook_effectiveness,
                "pattern_interrupt_count": retention_analysis.pattern_interrupt_count,
                "recommendations": retention_analysis.recommendations,
            },
            "quality_metrics": script.metadata.get("quality_metrics", {}),
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ============================================================================
# METADATA OPTIMIZATION TASKS
# ============================================================================

@celery_app.task(bind=True)
def optimize_video_metadata(
    self,
    niche: str,
    topic: str,
    script_title: Optional[str] = None,
    script_content: Optional[str] = None,
    platform: str = "youtube",
    video_format: str = "standard",
) -> Dict[str, Any]:
    """
    Generate optimized metadata for a video.
    
    Args:
        niche: Content niche
        topic: Video topic
        script_title: Optional script title
        script_content: Optional script content
        platform: Target platform (youtube, youtube_shorts, etc.)
        video_format: Video format (standard, shorts)
        
    Returns:
        Dict with optimized metadata
    """
    try:
        # Initialize optimizer
        global _metadata_optimizer
        if _metadata_optimizer is None:
            _metadata_optimizer = AlgorithmOptimizer(
                openai_client=get_openai_client(),
                db=get_db()
            )
        
        # Create request
        request = MetadataGenerationRequest(
            niche=niche,
            topic=topic,
            script_title=script_title,
            script_content=script_content,
            platform=platform,
            video_format=video_format,
        )
        
        # Generate metadata
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            metadata = loop.run_until_complete(_metadata_optimizer.generate_metadata(request))
        finally:
            loop.close()
        
        # Convert to serializable format
        title_variants = []
        for tv in metadata.title_variants:
            title_variants.append({
                "text": tv.text,
                "style": tv.style,
                "ctr_score": tv.ctr_score,
                "character_count": tv.character_count,
                "has_numbers": tv.has_numbers,
                "has_question": tv.has_question,
            })
        
        description_sections = []
        for ds in metadata.description_sections:
            description_sections.append({
                "type": ds.type,
                "content": ds.content,
                "order": ds.order,
            })
        
        return {
            "success": True,
            "metadata": {
                "primary_title": metadata.primary_title,
                "best_title": metadata.best_title,
                "title_variants": title_variants,
                "description": metadata.description,
                "description_sections": description_sections,
                "tags": metadata.tags,
                "hashtags": metadata.hashtags,
                "category_id": metadata.category_id,
                "thumbnail_text": metadata.thumbnail_text,
                "thumbnail_style": metadata.thumbnail_style,
                "pinned_comment": metadata.pinned_comment,
                "community_post_text": metadata.community_post_text,
                "optimal_publish_time": metadata.optimal_publish_time,
                "seo_score": metadata.seo_score,
                "ctr_score": metadata.ctr_score,
            },
            "platform": platform,
            "recommendations": _metadata_optimizer.get_platform_config(platform).__dict__,
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


# ============================================================================
# CONTENT VARIATION TASKS
# ============================================================================

@celery_app.task(bind=True)
def generate_content_variation(
    self,
    niche: str,
    topic: str,
    existing_fingerprints: Optional[List[str]] = None,
    min_uniqueness_score: float = 0.7,
    variation_strength: float = 0.5,
) -> Dict[str, Any]:
    """
    Generate content variation profile for uniqueness.
    
    Args:
        niche: Content niche
        topic: Video topic
        existing_fingerprints: List of existing content fingerprints
        min_uniqueness_score: Minimum uniqueness required
        variation_strength: How much to vary content
        
    Returns:
        Dict with variation profile and uniqueness metrics
    """
    try:
        # Initialize engine
        global _variation_engine
        if _variation_engine is None:
            _variation_engine = ContentVariationEngine(db=get_db())
        
        # Create request
        request = VariationRequest(
            niche=niche,
            topic=topic,
            existing_content_fingerprints=existing_fingerprints or [],
            min_uniqueness_score=min_uniqueness_score,
            variation_strength=variation_strength,
        )
        
        # Generate variation
        result = _variation_engine.generate_variation_profile(request)
        
        # Get diversity report
        diversity_report = _variation_engine.get_diversity_report(niche)
        
        return {
            "success": True,
            "variation_profile": {
                "profile_id": result.profile.profile_id,
                "tone": result.profile.tone,
                "narrative_style": result.profile.narrative_style,
                "perspective": result.profile.perspective,
                "pacing": result.profile.pacing,
                "energy_level": result.profile.energy_level,
                "formality": result.profile.formality,
            },
            "uniqueness_score": result.uniqueness_score,
            "similarity_to_existing": result.similarity_to_existing,
            "variations_applied": result.variations_applied,
            "recommendations": result.recommendations,
            "diversity_report": {
                "tone_diversity": diversity_report.tone_diversity,
                "style_diversity": diversity_report.style_diversity,
                "tone_distribution": diversity_report.tone_distribution,
                "underrepresented_tones": diversity_report.underrepresented_tones,
            },
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


# ============================================================================
# UPLOAD SCHEDULING TASKS
# ============================================================================

@celery_app.task(bind=True)
def schedule_video_upload(
    self,
    video_path: str,
    niche: str,
    topic: str,
    title: str,
    metadata: Optional[Dict[str, Any]] = None,
    thumbnail_path: Optional[str] = None,
    priority: str = "normal",
    scheduled_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Schedule a video for upload with rate limiting.
    
    Args:
        video_path: Path to video file
        niche: Content niche
        topic: Video topic
        title: Video title
        metadata: Video metadata
        thumbnail_path: Path to thumbnail
        priority: Upload priority (critical, high, normal, low)
        scheduled_time: Optional scheduled upload time (ISO format)
        
    Returns:
        Dict with upload job details
    """
    try:
        # Initialize optimizer
        global _upload_optimizer
        if _upload_optimizer is None:
            _upload_optimizer = UploadStrategyOptimizer(db=get_db())
        
        # Map priority string to enum
        priority_map = {
            "critical": UploadPriority.CRITICAL,
            "high": UploadPriority.HIGH,
            "normal": UploadPriority.NORMAL,
            "low": UploadPriority.LOW,
        }
        upload_priority = priority_map.get(priority.lower(), UploadPriority.NORMAL)
        
        # Parse scheduled time
        from datetime import datetime
        scheduled_dt = None
        if scheduled_time:
            try:
                scheduled_dt = datetime.fromisoformat(scheduled_time)
            except ValueError:
                pass
        
        # Create upload job
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            job = loop.run_until_complete(
                _upload_optimizer.create_upload_job(
                    video_path=video_path,
                    niche=niche,
                    topic=topic,
                    title=title,
                    metadata=metadata,
                    thumbnail_path=thumbnail_path,
                    priority=upload_priority,
                    scheduled_time=scheduled_dt,
                )
            )
        finally:
            loop.close()
        
        return {
            "success": True,
            "job": {
                "job_id": job.job_id,
                "status": job.status.value,
                "priority": job.priority.value,
                "scheduled_time": job.scheduled_time.isoformat() if job.scheduled_time else None,
                "created_at": job.created_at.isoformat(),
            },
            "rate_limit_status": _upload_optimizer.get_rate_limit_status(),
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def process_upload_queue(self) -> Dict[str, Any]:
    """
    Process the next upload in the queue.
    
    Returns:
        Dict with processing result
    """
    try:
        global _upload_optimizer
        if _upload_optimizer is None:
            _upload_optimizer = UploadStrategyOptimizer(db=get_db())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            job = loop.run_until_complete(_upload_optimizer.process_next_upload())
        finally:
            loop.close()
        
        if not job:
            return {
                "success": True,
                "processed": False,
                "reason": "No jobs in queue or rate limited",
            }
        
        return {
            "success": True,
            "processed": True,
            "job": {
                "job_id": job.job_id,
                "status": job.status.value,
                "topic": job.topic,
                "title": job.title,
                "youtube_video_id": job.youtube_video_id,
                "youtube_url": job.youtube_url,
            },
            "rate_limit_status": _upload_optimizer.get_rate_limit_status(),
        }
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery_app.task
def get_upload_queue_status() -> Dict[str, Any]:
    """
    Get current upload queue status.
    
    Returns:
        Dict with queue status
    """
    try:
        global _upload_optimizer
        if _upload_optimizer is None:
            _upload_optimizer = UploadStrategyOptimizer(db=get_db())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status = loop.run_until_complete(_upload_optimizer.get_queue_status())
        finally:
            loop.close()
        
        return {
            "success": True,
            "queue_status": {
                "total_jobs": status.total_jobs,
                "pending_jobs": status.pending_jobs,
                "processing_jobs": status.processing_jobs,
                "scheduled_jobs": status.scheduled_jobs,
                "failed_jobs": status.failed_jobs,
                "can_upload": status.can_upload,
                "rate_limit_reason": status.rate_limit_reason,
                "uploads_today": status.uploads_today,
                "daily_limit": status.daily_limit,
                "remaining_today": status.remaining_today,
            },
        }
        
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================================
# PIPELINE ORCHESTRATION TASKS
# ============================================================================

@celery_app.task(bind=True)
def run_viral_content_pipeline(
    self,
    niche: str,
    topic: Optional[str] = None,
    auto_upload: bool = False,
    target_duration_sec: int = 90,
    creativity_factor: float = 0.7,
) -> Dict[str, Any]:
    """
    Run the complete viral content generation pipeline.
    
    Args:
        niche: Content niche
        topic: Optional specific topic (discovers if not provided)
        auto_upload: Whether to auto-upload after generation
        target_duration_sec: Target video duration
        creativity_factor: Creativity level
        
    Returns:
        Dict with pipeline results
    """
    results = {
        "success": True,
        "niche": niche,
        "steps": {},
    }
    
    try:
        # Step 1: Discover topics (if not provided)
        if not topic:
            topic_result = discover_viral_topics(
                niche=niche,
                max_topics=1,
                min_virality_score=70,
            )
            
            if not topic_result.get("success") or not topic_result.get("topics"):
                results["success"] = False
                results["error"] = "No viral topics discovered"
                return results
            
            topic = topic_result["topics"][0]["topic"]
            results["steps"]["discovery"] = topic_result
        
        # Step 2: Generate script
        script_result = generate_viral_script(
            niche=niche,
            topic=topic,
            target_duration_sec=target_duration_sec,
            creativity_factor=creativity_factor,
        )
        
        if not script_result.get("success"):
            results["success"] = False
            results["error"] = "Script generation failed"
            return results
        
        results["steps"]["script"] = script_result
        
        # Step 3: Optimize metadata
        metadata_result = optimize_video_metadata(
            niche=niche,
            topic=topic,
            script_title=script_result["script"]["title"],
            script_content=script_result["script"]["full_text"],
        )
        
        if not metadata_result.get("success"):
            results["success"] = False
            results["error"] = "Metadata optimization failed"
            return results
        
        results["steps"]["metadata"] = metadata_result
        
        # Step 4: Generate variation profile
        variation_result = generate_content_variation(
            niche=niche,
            topic=topic,
        )
        
        results["steps"]["variation"] = variation_result
        
        # Step 5: Schedule upload (if requested)
        if auto_upload:
            # Note: In production, video would need to be generated first
            results["steps"]["upload"] = {
                "status": "pending",
                "message": "Video generation required before upload",
            }
        
        return results
        
    except Exception as exc:
        results["success"] = False
        results["error"] = str(exc)
        raise self.retry(exc=exc, countdown=120)


# ============================================================================
# UTILITY TASKS
# ============================================================================

@celery_app.task
def get_available_niches() -> Dict[str, Any]:
    """Get all available niches."""
    try:
        niches = niche_config_manager.get_all_niches()
        return {
            "success": True,
            "niches": niches,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@celery_app.task
def get_niche_config(niche: str) -> Dict[str, Any]:
    """Get configuration for a specific niche."""
    try:
        config = niche_config_manager.get_niche_by_value(niche)
        
        if not config:
            return {
                "success": False,
                "error": f"Unknown niche: {niche}",
            }
        
        return {
            "success": True,
            "config": {
                "niche": config.niche.value,
                "display_name": config.display_name,
                "description": config.description,
                "target_duration_sec": config.target_duration_sec,
                "preferred_voices": config.preferred_voices,
                "hook_strategies": [h.value for h in config.hook_strategies],
                "emotional_triggers": [e.value for e in config.emotional_triggers],
                "daily_upload_limit": config.daily_upload_limit,
                "optimal_posting_times": config.optimal_posting_times,
                "title_patterns": config.title_patterns,
            },
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }
