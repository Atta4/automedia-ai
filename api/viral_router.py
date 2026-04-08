"""
FastAPI Router for Multi-Niche Viral Content Engine

Provides REST endpoints for:
- Niche management
- Viral topic discovery
- Script generation
- Metadata optimization
- Upload scheduling
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v2/viral", tags=["Viral Content Engine"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TopicDiscoveryRequest(BaseModel):
    """Request for viral topic discovery."""
    niche: str
    region: str = "US"
    language: str = "en"
    max_topics: int = 10
    min_virality_score: int = 60
    exclude_keywords: List[str] = Field(default_factory=list)


class ScriptGenerationRequest(BaseModel):
    """Request for viral script generation."""
    niche: str
    topic: str
    target_duration_sec: int = 90
    creativity_factor: float = 0.7
    hook_framework: Optional[str] = None


class MetadataOptimizationRequest(BaseModel):
    """Request for metadata optimization."""
    niche: str
    topic: str
    script_title: Optional[str] = None
    script_content: Optional[str] = None
    platform: str = "youtube"
    video_format: str = "standard"


class UploadScheduleRequest(BaseModel):
    """Request for upload scheduling."""
    video_path: str
    niche: str
    topic: str
    title: str
    metadata: Optional[Dict[str, Any]] = None
    thumbnail_path: Optional[str] = None
    priority: str = "normal"
    scheduled_time: Optional[str] = None


class PipelineRequest(BaseModel):
    """Request for full pipeline execution."""
    niche: str
    topic: Optional[str] = None
    auto_upload: bool = False
    target_duration_sec: int = 90
    creativity_factor: float = 0.7


# ============================================================================
# Niche Management Endpoints
# ============================================================================

@router.get("/niches")
async def get_available_niches():
    """
    Get all available content niches.
    
    Returns list of supported niches with their configurations.
    """
    from config.niche_config import niche_config_manager
    
    try:
        niches = niche_config_manager.get_all_niches()
        return {
            "success": True,
            "niches": niches,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/niches/{niche}")
async def get_niche_configuration(niche: str):
    """
    Get detailed configuration for a specific niche.
    
    Includes:
    - Target duration
    - Preferred voices
    - Hook strategies
    - Emotional triggers
    - Upload limits
    - Optimal posting times
    """
    from config.niche_config import niche_config_manager
    
    config = niche_config_manager.get_niche_by_value(niche)
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Niche '{niche}' not found. Available niches: {', '.join([n.value for n in config_manager.get_all_niches()])}"
        )
    
    return {
        "success": True,
        "config": {
            "niche": config.niche.value,
            "display_name": config.display_name,
            "description": config.description,
            "target_duration_sec": config.target_duration_sec,
            "hook_duration_sec": config.hook_duration_sec,
            "preferred_voices": config.preferred_voices,
            "voice_speed": config.voice_speed,
            "hook_strategies": [h.value for h in config.hook_strategies],
            "emotional_triggers": [e.value for e in config.emotional_triggers],
            "daily_upload_limit": config.daily_upload_limit,
            "upload_priority": config.upload_priority,
            "optimal_posting_times": config.optimal_posting_times,
            "title_patterns": config.title_patterns,
            "thumbnail_styles": config.thumbnail_styles,
            "visual_style": config.visual_style,
            "color_palette": config.color_palette,
            "category_id": config.category_id,
            "cta_style": config.cta_style,
        },
    }


@router.get("/niches/{niche}/sources")
async def get_niche_sources(niche: str):
    """Get recommended topic discovery sources for a niche."""
    from modules.niche_manager import NicheManager
    
    manager = NicheManager()
    sources = manager.get_topic_sources(niche)
    
    return {
        "success": True,
        "niche": niche,
        "sources": sources,
    }


@router.get("/niches/{niche}/optimal-time")
async def get_optimal_posting_time(niche: str):
    """Get optimal posting time for a niche."""
    from modules.niche_manager import NicheManager
    
    manager = NicheManager()
    optimal_time = manager.get_optimal_posting_time(niche)
    
    return {
        "success": True,
        "niche": niche,
        "optimal_posting_time": optimal_time,
    }


# ============================================================================
# Topic Discovery Endpoints
# ============================================================================

@router.post("/topics/discover")
async def discover_viral_topics(request: TopicDiscoveryRequest = None):
    """
    Discover viral topics for a specific niche.

    Uses smart discovery engine to find trending topics with high virality potential.
    Each topic includes:
    - Virality score (0-100)
    - Emotional triggers
    - CTR patterns
    - Validation status
    """
    from modules.smart_discovery import SmartTopicDiscoveryEngine, TopicGenerationRequest
    from core.database import get_db
    from config.settings import get_settings

    # Handle None request (use defaults)
    if request is None:
        request = TopicDiscoveryRequest(niche="motivation")

    # Get focus keywords from settings
    settings = get_settings()
    focus_keywords = settings.get_focus_keywords()

    try:
        db = await get_db()
        engine = SmartTopicDiscoveryEngine(db=db)

        gen_request = TopicGenerationRequest(
            niche=request.niche,
            region=request.region,
            language=request.language,
            max_topics=request.max_topics,
            min_virality_score=request.min_virality_score,
            exclude_keywords=request.exclude_keywords or [],
            focus_keywords=focus_keywords,  # Add focus keywords
        )

        result = await engine.discover_topics(gen_request)

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
            "niche": request.niche,
            "topics": topics,
            "total_discovered": result.total_discovered,
            "total_validated": result.total_validated,
            "avg_virality_score": result.avg_virality_score,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/score")
async def score_topic_virality(
    niche: str = Body(..., embed=True),
    topic: str = Body(..., embed=True),
):
    """
    Calculate virality score for a specific topic.
    
    Useful for validating user-provided topics before generation.
    """
    from modules.smart_discovery import SmartTopicDiscoveryEngine
    from core.database import get_db

    try:
        db = await get_db()
        engine = SmartTopicDiscoveryEngine(db=db)
        
        result = await engine.discover_single_topic(niche, topic)
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Could not score topic. Topic may be invalid.",
            )
        
        return {
            "success": True,
            "topic": topic,
            "niche": niche,
            "virality_score": result.virality_score.overall,
            "breakdown": engine.get_virality_breakdown(result),
            "emotional_triggers": result.emotional_triggers,
            "ctr_patterns": result.ctr_patterns,
            "recommendation": "High potential - proceed with generation" 
                              if result.virality_score.overall >= 70 
                              else "Moderate potential - consider optimization",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Script Generation Endpoints
# ============================================================================

@router.post("/scripts/generate")
async def generate_viral_script(request: ScriptGenerationRequest):
    """
    Generate a viral-optimized script for a topic.
    
    Uses proven hook frameworks and retention optimization:
    - Hook (first 3 seconds)
    - Open loop (curiosity)
    - Fast pacing
    - Retention hooks every 5-8 seconds
    - Strong ending with CTA
    """
    from modules.viral_script_generator import ViralScriptGenerator, ScriptGenerationRequest
    from config.niche_config import niche_config_manager
    from config.settings import get_settings
    from openai import AsyncOpenAI

    # Validate niche
    config = niche_config_manager.get_niche_by_value(request.niche)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown niche: {request.niche}",
        )

    try:
        settings = get_settings()
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        generator = ViralScriptGenerator(openai_client=openai_client)

        gen_request = ScriptGenerationRequest(
            niche=request.niche,
            topic=request.topic,
            target_duration_sec=request.target_duration_sec,
            creativity_factor=request.creativity_factor,
            hook_framework=request.hook_framework,
        )

        script = await generator.generate_script(gen_request)

        # Convert segments to serializable format
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
        retention_analysis = generator.analyze_retention(script)
        
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
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Metadata Optimization Endpoints
# ============================================================================

@router.post("/metadata/optimize")
async def optimize_metadata(request: MetadataOptimizationRequest):
    """
    Generate optimized metadata for a video.
    
    Includes:
    - CTR-optimized titles (multiple variants)
    - SEO-optimized description
    - Search-optimized tags
    - Hashtags
    - Thumbnail text suggestions
    - Pinned comment
    - Community post
    """
    from modules.algorithm_optimizer import AlgorithmOptimizer, MetadataGenerationRequest
    from config.settings import get_settings
    from openai import AsyncOpenAI

    try:
        settings = get_settings()
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        optimizer = AlgorithmOptimizer(openai_client=openai_client)

        meta_request = MetadataGenerationRequest(
            niche=request.niche,
            topic=request.topic,
            script_title=request.script_title,
            script_content=request.script_content,
            platform=request.platform,
            video_format=request.video_format,
        )

        metadata = await optimizer.generate_metadata(meta_request)
        
        # Convert to serializable format
        title_variants = []
        for tv in metadata.title_variants:
            title_variants.append({
                "text": tv.text,
                "style": tv.style,
                "ctr_score": tv.ctr_score,
                "character_count": tv.character_count,
            })
        
        return {
            "success": True,
            "metadata": {
                "primary_title": metadata.primary_title,
                "best_title": metadata.best_title,
                "title_variants": title_variants,
                "description": metadata.description,
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
            "platform": request.platform,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Content Variation Endpoints
# ============================================================================

@router.post("/variation/generate")
async def generate_content_variation(
    niche: str = Body(..., embed=True),
    topic: str = Body(..., embed=True),
    existing_fingerprints: Optional[List[str]] = None,
    min_uniqueness_score: float = 0.7,
):
    """
    Generate content variation profile for uniqueness.
    
    Ensures each video feels unique by varying:
    - Tone
    - Sentence structure
    - Storytelling style
    - Pacing
    """
    from modules.content_variation import ContentVariationEngine, VariationRequest
    
    try:
        engine = ContentVariationEngine()
        
        request = VariationRequest(
            niche=niche,
            topic=topic,
            existing_content_fingerprints=existing_fingerprints or [],
            min_uniqueness_score=min_uniqueness_score,
        )
        
        result = engine.generate_variation_profile(request)
        diversity_report = engine.get_diversity_report(niche)
        
        return {
            "success": True,
            "variation_profile": {
                "profile_id": result.profile.profile_id,
                "tone": result.profile.tone,
                "narrative_style": result.profile.narrative_style,
                "perspective": result.profile.perspective,
                "pacing": result.profile.pacing,
                "energy_level": result.profile.energy_level,
            },
            "uniqueness_score": result.uniqueness_score,
            "similarity_to_existing": result.similarity_to_existing,
            "variations_applied": result.variations_applied,
            "recommendations": result.recommendations,
            "diversity_report": {
                "tone_diversity": diversity_report.tone_diversity,
                "style_diversity": diversity_report.style_diversity,
                "tone_distribution": diversity_report.tone_distribution,
            },
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Upload Scheduling Endpoints
# ============================================================================

@router.post("/upload/schedule")
async def schedule_upload(request: UploadScheduleRequest):
    """
    Schedule a video for upload with rate limiting.
    
    Features:
    - Smart rate limiting
    - Optimal timing scheduling
    - Priority-based queue
    - Automatic retry on failure
    """
    from modules.upload_optimizer import UploadStrategyOptimizer, UploadPriority
    from datetime import datetime
    
    try:
        optimizer = UploadStrategyOptimizer()
        
        # Map priority
        priority_map = {
            "critical": UploadPriority.CRITICAL,
            "high": UploadPriority.HIGH,
            "normal": UploadPriority.NORMAL,
            "low": UploadPriority.LOW,
        }
        upload_priority = priority_map.get(request.priority.lower(), UploadPriority.NORMAL)
        
        # Parse scheduled time
        scheduled_dt = None
        if request.scheduled_time:
            try:
                scheduled_dt = datetime.fromisoformat(request.scheduled_time)
            except ValueError:
                pass
        
        job = await optimizer.create_upload_job(
            video_path=request.video_path,
            niche=request.niche,
            topic=request.topic,
            title=request.title,
            metadata=request.metadata,
            thumbnail_path=request.thumbnail_path,
            priority=upload_priority,
            scheduled_time=scheduled_dt,
        )
        
        return {
            "success": True,
            "job": {
                "job_id": job.job_id,
                "status": job.status.value,
                "priority": job.priority.value,
                "scheduled_time": job.scheduled_time.isoformat() if job.scheduled_time else None,
                "created_at": job.created_at.isoformat(),
            },
            "rate_limit_status": optimizer.get_rate_limit_status(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/queue/status")
async def get_upload_queue_status():
    """Get current upload queue status."""
    from modules.upload_optimizer import UploadStrategyOptimizer
    
    try:
        optimizer = UploadStrategyOptimizer()
        status = await optimizer.get_queue_status()
        
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/rate-limit")
async def get_rate_limit_status():
    """Get current rate limit status."""
    from modules.upload_optimizer import UploadStrategyOptimizer
    
    try:
        optimizer = UploadStrategyOptimizer()
        rate_status = optimizer.get_rate_limit_status()
        
        return {
            "success": True,
            "rate_limit": rate_status,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Full Pipeline Endpoint
# ============================================================================

@router.post("/pipeline/run")
async def run_viral_pipeline(request: PipelineRequest):
    """
    Run the complete viral content generation pipeline.
    
    Steps:
    1. Discover viral topics (if topic not provided)
    2. Generate viral script
    3. Optimize metadata
    4. Generate content variation
    5. Schedule upload (if auto_upload=True)
    
    Returns complete pipeline results with all generated content.
    """
    from modules.smart_discovery import SmartTopicDiscoveryEngine, TopicGenerationRequest
    from modules.viral_script_generator import ViralScriptGenerator, ScriptGenerationRequest
    from modules.algorithm_optimizer import AlgorithmOptimizer, MetadataGenerationRequest
    from modules.content_variation import ContentVariationEngine, VariationRequest
    from config.niche_config import niche_config_manager
    from config.settings import get_settings
    from openai import AsyncOpenAI

    results = {
        "success": True,
        "niche": request.niche,
        "steps": {},
    }

    try:
        # Validate niche
        config = niche_config_manager.get_niche_by_value(request.niche)
        if not config:
            raise HTTPException(status_code=400, detail=f"Unknown niche: {request.niche}")

        settings = get_settings()
        openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        topic = request.topic

        # Step 1: Discover topics (if not provided)
        if not topic:
            discovery_engine = SmartTopicDiscoveryEngine()
            disc_request = TopicGenerationRequest(
                niche=request.niche,
                max_topics=1,
                min_virality_score=70,
            )
            disc_result = await discovery_engine.discover_topics(disc_request)
            
            if not disc_result.topics:
                raise HTTPException(status_code=404, detail="No viral topics discovered")
            
            topic = disc_result.topics[0].topic
            results["steps"]["discovery"] = {
                "topic": topic,
                "virality_score": disc_result.topics[0].virality_score.overall,
            }
        
        # Step 2: Generate script
        script_generator = ViralScriptGenerator(openai_client=openai_client)
        gen_request = ScriptGenerationRequest(
            niche=request.niche,
            topic=topic,
            target_duration_sec=request.target_duration_sec,
            creativity_factor=request.creativity_factor,
        )
        script = await script_generator.generate_script(gen_request)

        results["steps"]["script"] = {
            "title": script.title,
            "hook_framework": script.hook_framework.value,
            "estimated_duration_sec": script.estimated_duration_sec,
            "retention_score": script.retention_score,
        }

        # Step 3: Optimize metadata
        metadata_optimizer = AlgorithmOptimizer(openai_client=openai_client)
        meta_request = MetadataGenerationRequest(
            niche=request.niche,
            topic=topic,
            script_title=script.title,
            script_content=script.full_text,
        )
        metadata = await metadata_optimizer.generate_metadata(meta_request)
        
        results["steps"]["metadata"] = {
            "primary_title": metadata.primary_title,
            "seo_score": metadata.seo_score,
            "ctr_score": metadata.ctr_score,
        }
        
        # Step 4: Generate variation profile
        variation_engine = ContentVariationEngine()
        var_request = VariationRequest(
            niche=request.niche,
            topic=topic,
        )
        var_result = variation_engine.generate_variation_profile(var_request)
        
        results["steps"]["variation"] = {
            "profile_id": var_result.profile.profile_id,
            "tone": var_result.profile.tone,
            "uniqueness_score": var_result.uniqueness_score,
        }
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
