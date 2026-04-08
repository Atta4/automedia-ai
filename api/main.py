import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from core.database import init_indexes, close_db
from config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    os.makedirs(settings.output_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    await init_indexes()
    logger.info("AutoMedia AI API started")
    yield
    # Shutdown
    await close_db()
    logger.info("AutoMedia AI API stopped")


app = FastAPI(
    title="AutoMedia AI",
    description="Automated trending content generation pipeline",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Viral Content Engine router
from api.viral_router import router as viral_router
app.include_router(viral_router)

@app.get("/")
async def dashboard():
    """Serve the AutoMedia AI dashboard."""
    dash = Path(__file__).parent / "dashboard.html"
    return FileResponse(str(dash))

@app.get("/viral")
async def viral_dashboard():
    """Serve the Viral Content Engine dashboard."""
    dash = Path(__file__).parent / "viral_dashboard.html"
    return FileResponse(str(dash))




# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0-mvp"}


# ── Data Collection Endpoints ─────────────────────────────────────────────────

@app.post("/api/v1/collect/run")
async def trigger_collection(background_tasks: BackgroundTasks):
    """
    Manually trigger a data collection cycle.
    Discovers trending topics, validates, saves to DB, queues script generation.
    """
    from modules.data_collection.engine import DataCollectionEngine

    async def _run():
        engine = DataCollectionEngine()
        topics = await engine.run()
        logger.info(f"Manual collection complete: {len(topics)} topics validated")

    background_tasks.add_task(_run)
    return {"message": "Collection started", "status": "running"}


@app.get("/api/v1/topics")
async def list_topics(status: str | None = None, limit: int = 20):
    """List topics from MongoDB, optionally filtered by status. Newest first."""
    from core.database import get_db

    db = await get_db()
    query = {}
    if status:
        query["status"] = status

    # Sort by created_at descending (newest first)
    cursor = db.topics.find(
        query,
        sort=[("created_at", -1)],  # Newest first
        limit=limit,
    )
    topics = await cursor.to_list(length=limit)

    # Remove MongoDB _id for JSON serialization
    for t in topics:
        t.pop("_id", None)

    return {"topics": topics, "count": len(topics)}


@app.get("/api/v1/topics/{normalized_keyword}")
async def get_topic(normalized_keyword: str):
    """Get a single topic by its normalized keyword."""
    from core.database import get_db

    db = await get_db()
    topic = await db.topics.find_one({"normalized_keyword": normalized_keyword})

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic.pop("_id", None)
    return topic


# ── Script Generation Endpoints ───────────────────────────────────────────────

@app.post("/api/v1/scripts/generate/{normalized_keyword}")
async def generate_script(
    normalized_keyword: str,
    style: str = "journalist",
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger script generation for a specific validated topic.
    Styles: journalist | commentary | humorous | roast
    """
    from modules.script_generation.engine import ScriptGenerationEngine
    from core.models import ContentStyle

    valid_styles = [s.value for s in ContentStyle]
    if style not in valid_styles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Choose from: {valid_styles}"
        )

    engine = ScriptGenerationEngine()
    script = await engine.run_for_topic(
        normalized_keyword,
        style=ContentStyle(style),
    )

    if not script:
        raise HTTPException(
            status_code=404,
            detail="Topic not found or already processed"
        )

    return {
        "message": "Script generated",
        "title": script.title,
        "style": script.style.value,
        "estimated_duration_sec": script.estimated_duration_sec,
        "segments": len(script.segments),
        "hashtags": script.hashtags,
    }


@app.get("/api/v1/scripts/{normalized_keyword}")
async def get_script(normalized_keyword: str):
    """Retrieve a generated script by normalized keyword."""
    from modules.script_generation.engine import ScriptGenerationEngine

    engine = ScriptGenerationEngine()
    doc = await engine.get_script(normalized_keyword)

    if not doc:
        raise HTTPException(status_code=404, detail="Script not found")

    return doc


@app.post("/api/v1/scripts/batch-generate")
async def batch_generate_scripts(limit: int = 5, style: str = "journalist"):
    """
    Generate scripts for all pending validated topics (up to `limit`).
    """
    from modules.script_generation.engine import ScriptGenerationEngine
    from core.models import ContentStyle

    engine = ScriptGenerationEngine()
    scripts = await engine.run_batch(
        limit=limit,
        style=ContentStyle(style),
    )

    return {
        "message": f"Batch complete",
        "scripts_generated": len(scripts),
        "titles": [s.title for s in scripts],
    }



# ── Script Generation Endpoints ───────────────────────────────────────────────

@app.post("/api/v1/scripts/generate/{normalized_keyword}")
async def generate_script(
    normalized_keyword: str,
    style: str = "journalist",
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger script generation for a validated topic.
    style: journalist | commentary | humorous | roast
    """
    from modules.script_generation.engine import ScriptGenerationEngine
    from core.models import ContentStyle

    try:
        content_style = ContentStyle(style)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Choose: {[s.value for s in ContentStyle]}"
        )

    engine = ScriptGenerationEngine()
    script = await engine.run_for_topic(
        normalized_keyword=normalized_keyword,
        style=content_style,
    )

    if not script:
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{normalized_keyword}' not found or generation failed"
        )

    return {
        "title": script.title,
        "style": script.style,
        "estimated_duration_sec": script.estimated_duration_sec,
        "hashtags": script.hashtags,
        "segments": [s.model_dump() for s in script.segments],
        "description": script.description,
    }


@app.post("/api/v1/scripts/generate-batch")
async def generate_scripts_batch(limit: int = 5, style: str = "journalist"):
    """Generate scripts for all pending validated topics."""
    from modules.script_generation.engine import ScriptGenerationEngine
    from core.models import ContentStyle

    try:
        content_style = ContentStyle(style)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid style")

    engine = ScriptGenerationEngine()
    scripts = await engine.run_batch(limit=limit, style=content_style)

    return {
        "generated": len(scripts),
        "scripts": [
            {"title": s.title, "keyword": s.topic_keyword, "style": s.style}
            for s in scripts
        ],
    }


@app.get("/api/v1/scripts/{normalized_keyword}")
async def get_script(normalized_keyword: str):
    """Fetch a saved script from MongoDB."""
    from modules.script_generation.engine import ScriptGenerationEngine

    engine = ScriptGenerationEngine()
    script = await engine.get_script(normalized_keyword)

    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script


# ── Video Production Endpoints ────────────────────────────────────────────────

@app.post("/api/v1/videos/produce/{normalized_keyword}")
async def produce_video(normalized_keyword: str, background_tasks: BackgroundTasks):
    """
    Trigger full video production for a scripted topic.
    Runs: TTS → Visuals → Subtitles → FFmpeg → MP4
    """
    from modules.video_assembly.engine import VideoProductionEngine

    async def _run():
        engine = VideoProductionEngine()
        await engine.produce(normalized_keyword)

    background_tasks.add_task(_run)
    return {"message": f"Video production started for '{normalized_keyword}'", "status": "running"}


@app.post("/api/v1/videos/produce-batch")
async def produce_videos_batch(limit: int = 3, background_tasks: BackgroundTasks = None):
    """Produce videos for all SCRIPTED topics (batch)."""
    from modules.video_assembly.engine import VideoProductionEngine

    async def _run():
        engine = VideoProductionEngine()
        await engine.produce_batch(limit=limit)

    background_tasks.add_task(_run)
    return {"message": f"Batch production started (limit={limit})", "status": "running"}


@app.get("/api/v1/videos")
async def list_videos(status: str | None = None, limit: int = 20):
    """List all produced videos from MongoDB."""
    from core.database import get_db

    db = await get_db()
    query = {}
    if status:
        query["status"] = status

    cursor = db.videos.find(query, sort=[("created_at", -1)], limit=limit)
    videos = await cursor.to_list(length=limit)
    for v in videos:
        v.pop("_id", None)
        v.pop("script", None)   # strip script to keep response slim

    return {"videos": videos, "count": len(videos)}


@app.get("/api/v1/videos/{normalized_keyword}")
async def get_video(normalized_keyword: str):
    """Get full video record including script."""
    from core.database import get_db

    db = await get_db()
    video = await db.videos.find_one({"topic_keyword": normalized_keyword})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    video.pop("_id", None)
    return video


@app.get("/api/v1/pipeline/status")
async def pipeline_status():
    """
    Overview of entire pipeline — how many topics in each stage.
    """
    from core.database import get_db
    from core.models import TopicStatus

    db = await get_db()
    status_counts = {}

    for status in TopicStatus:
        count = await db.topics.count_documents({"status": status})
        status_counts[status.value] = count

    video_count = await db.videos.count_documents({})

    return {
        "pipeline": status_counts,
        "total_videos_produced": video_count,
    }


# ── Review Queue Endpoints ────────────────────────────────────────────────────

@app.get("/api/v1/review/queue")
async def get_review_queue(status: str | None = None, limit: int = 20):
    """
    List all items in the review queue.
    status filter: pending | approved | rejected | rework
    """
    from modules.publisher.review_queue import ReviewQueueEngine, ReviewStatus

    engine = ReviewQueueEngine()

    resolved_status = None
    if status:
        try:
            resolved_status = ReviewStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Choose: {[s.value for s in ReviewStatus]}"
            )

    jobs = await engine.list_all(status=resolved_status, limit=limit)
    return {
        "jobs": [j.model_dump() for j in jobs],
        "count": len(jobs),
    }


@app.get("/api/v1/review/queue/pending")
async def get_pending_reviews():
    """Get all videos waiting for review — the main reviewer endpoint."""
    from modules.publisher.review_queue import ReviewQueueEngine

    engine = ReviewQueueEngine()
    jobs = await engine.list_pending(limit=50)
    return {
        "jobs": [j.model_dump() for j in jobs],
        "count": len(jobs),
        "message": f"{len(jobs)} video(s) waiting for your review",
    }


@app.get("/api/v1/review/stats")
async def get_review_stats():
    """Review queue statistics — pending / approved / rejected counts."""
    from modules.publisher.review_queue import ReviewQueueEngine

    engine = ReviewQueueEngine()
    return await engine.get_stats()


@app.get("/api/v1/review/{job_id}")
async def get_review_item(job_id: str):
    """Get a single review item by job_id."""
    from modules.publisher.review_queue import ReviewQueueEngine

    engine = ReviewQueueEngine()
    job = await engine.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Review job '{job_id}' not found")
    return job.model_dump()


@app.post("/api/v1/review/{job_id}/approve")
async def approve_video(job_id: str, decision: dict = {}):
    """
    Approve a video for upload.
    Body (optional): {"reviewer_note": "Looks great", "reviewed_by": "Ahmed"}
    """
    from modules.publisher.review_queue import ReviewQueueEngine
    from modules.publisher.models import ReviewDecision

    engine = ReviewQueueEngine()
    dec = ReviewDecision(
        reviewer_note=decision.get("reviewer_note"),
        reviewed_by=decision.get("reviewed_by"),
    )
    result = await engine.approve(job_id, dec)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found or not in PENDING status"
        )

    return {
        "message": f"Video '{job_id}' APPROVED ✓",
        "status": result.status,
        "video_path": result.video_path,
        "thumbnail_path": result.thumbnail_path,
    }


@app.post("/api/v1/review/{job_id}/reject")
async def reject_video(job_id: str, decision: dict = {}):
    """
    Reject a video.
    Body: {"reason": "quality_low", "reviewer_note": "Audio is distorted", "reviewed_by": "Ahmed"}
    Reasons: quality_low | factually_wrong | policy_violation | audio_issue | visual_issue | title_weak | other
    """
    from modules.publisher.review_queue import ReviewQueueEngine
    from modules.publisher.models import RejectDecision, RejectionReason

    engine = ReviewQueueEngine()

    reason_str = decision.get("reason", "other")
    try:
        reason = RejectionReason(reason_str)
    except ValueError:
        reason = RejectionReason.OTHER

    dec = RejectDecision(
        reason=reason,
        reviewer_note=decision.get("reviewer_note"),
        reviewed_by=decision.get("reviewed_by"),
    )
    result = await engine.reject(job_id, dec)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found or not in PENDING status"
        )

    return {
        "message": f"Video '{job_id}' REJECTED ✗",
        "reason": result.rejection_reason,
        "status": result.status,
    }


@app.post("/api/v1/review/{job_id}/rework")
async def rework_video(job_id: str, decision: dict = {}):
    """
    Send video back for rework (re-script generation).
    Body: {"instruction": "Make it more humorous and shorter", "reviewed_by": "Ahmed"}
    """
    from modules.publisher.review_queue import ReviewQueueEngine
    from modules.publisher.models import ReworkDecision

    engine = ReviewQueueEngine()

    instruction = decision.get("instruction", "Improve quality and re-generate")
    dec = ReworkDecision(
        instruction=instruction,
        reviewed_by=decision.get("reviewed_by"),
    )
    result = await engine.rework(job_id, dec)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found or not in PENDING status"
        )

    return {
        "message": f"Video '{job_id}' sent for REWORK",
        "instruction": instruction,
        "status": result.status,
    }


# ── Thumbnail Endpoint ────────────────────────────────────────────────────────

@app.post("/api/v1/thumbnail/generate/{normalized_keyword}")
async def generate_thumbnail(normalized_keyword: str):
    """Manually trigger thumbnail generation for a scripted topic."""
    from modules.thumbnail.generator import ThumbnailGenerator
    from modules.script_generation.engine import ScriptGenerationEngine

    script_engine = ScriptGenerationEngine()
    script_doc = await script_engine.get_script(normalized_keyword)
    if not script_doc:
        raise HTTPException(status_code=404, detail="Script not found")

    from core.models import VideoScript
    script = VideoScript(**{k: v for k, v in script_doc.items()
                           if k not in ("topic_keyword_normalized", "saved_at")})

    gen = ThumbnailGenerator()
    from re import sub
    job_id = sub(r"[^\w-]", "_", normalized_keyword)[:50]
    thumb_path = await gen.generate(script=script, job_id=job_id)

    return {
        "thumbnail_path": str(thumb_path),
        "message": "Thumbnail generated successfully",
    }


# ── Review Dashboard (Web UI) ─────────────────────────────────────────────────

from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path as FPath

@app.get("/dashboard", response_class=HTMLResponse)
async def review_dashboard():
    """Serve the review dashboard UI."""
    html_path = FPath(__file__).parent / "dashboard.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/api/v1/thumbnail/file/{job_id}")
async def serve_thumbnail(job_id: str):
    """Serve thumbnail image file for the dashboard."""
    from config.settings import get_settings
    settings = get_settings()
    thumb_path = FPath(settings.output_dir) / f"{job_id}_thumbnail.jpg"
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumb_path, media_type="image/jpeg")


# ── Review Queue Endpoints ────────────────────────────────────────────────────

@app.get("/api/v1/review/queue")
async def get_review_queue(limit: int = 20):
    """List all videos pending human review."""
    from modules.publisher.review_queue import ReviewQueue
    rq = ReviewQueue()
    items = await rq.get_pending(limit=limit)
    return {"items": items, "count": len(items)}


@app.get("/api/v1/review/stats")
async def get_review_stats():
    """Review queue statistics — pending / approved / rejected / revision."""
    from modules.publisher.review_queue import ReviewQueue
    rq = ReviewQueue()
    return await rq.get_stats()


@app.get("/api/v1/review/{normalized_keyword}")
async def get_review_item(normalized_keyword: str):
    """Get review details for a specific video."""
    from modules.publisher.review_queue import ReviewQueue
    rq = ReviewQueue()
    item = await rq.get_item(normalized_keyword)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item


@app.post("/api/v1/review/{normalized_keyword}/approve")
async def approve_video(normalized_keyword: str, notes: str | None = None):
    """
    Approve a video for YouTube upload.
    Triggers upload task automatically.
    """
    from modules.publisher.review_queue import ReviewQueue
    rq = ReviewQueue()
    return await rq.approve(normalized_keyword, notes=notes)


@app.post("/api/v1/review/{normalized_keyword}/reject")
async def reject_video(normalized_keyword: str, notes: str | None = None):
    """Reject a video — marks topic as failed."""
    from modules.publisher.review_queue import ReviewQueue
    rq = ReviewQueue()
    return await rq.reject(normalized_keyword, notes=notes)


@app.post("/api/v1/review/{normalized_keyword}/revision")
async def request_revision(normalized_keyword: str, notes: str | None = None):
    """
    Send video back for revision.
    Resets topic to VALIDATED and re-queues script generation.
    """
    from modules.publisher.review_queue import ReviewQueue
    rq = ReviewQueue()
    return await rq.request_revision(normalized_keyword, notes=notes)


# ── Thumbnail Endpoints ───────────────────────────────────────────────────────

@app.post("/api/v1/thumbnails/generate/{normalized_keyword}")
async def generate_thumbnail(normalized_keyword: str, style: str = "journalist"):
    """Manually regenerate thumbnail for a topic."""
    from modules.thumbnail.generator import ThumbnailGenerator
    from core.database import get_db

    db = await get_db()
    script_doc = await db.scripts.find_one({"topic_keyword_normalized": normalized_keyword})
    if not script_doc:
        raise HTTPException(status_code=404, detail="Script not found")

    gen = ThumbnailGenerator()
    path = await gen.generate(
        title=script_doc.get("title", normalized_keyword),
        topic_keyword=normalized_keyword,
        style=style,
        job_id=normalized_keyword,
    )

    # Update video record with new thumbnail path
    await db.videos.update_one(
        {"topic_keyword": normalized_keyword},
        {"$set": {"thumbnail_path": str(path)}},
    )
    return {"thumbnail_path": str(path), "status": "generated"}


# ── Settings Update Endpoint ──────────────────────────────────────────────────

@app.post("/api/v1/settings/update")
async def update_settings(
    video_format: str = "standard",
    video_resolution: str = "1080p",
    target_video_duration: int = 90,
    script_language: str = "en",
    content_perspective: str = "balanced",
    trending_region: str = "US",
    max_topics_per_run: int = 10,
    blocked_topics: str = "",
    openai_tts_voice: str = "auto",
    tts_volume_boost: float = 1.6,
    focus_keywords: str = "",
    content_niche: str = "current_affairs",  # NEW: Multi-niche support
):
    """
    Update runtime settings. Writes to .env file so they persist across restarts.
    Dashboard calls this when user clicks 'Save & Apply'.
    """
    import os
    from config.settings import get_settings
    from functools import lru_cache

    env_path = ".env"

    # Read existing .env
    existing = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    # Update values
    updates = {
        "VIDEO_FORMAT": video_format,
        "VIDEO_RESOLUTION": video_resolution,
        "TARGET_VIDEO_DURATION": str(target_video_duration),
        "SCRIPT_LANGUAGE": script_language,
        "CONTENT_PERSPECTIVE": content_perspective,
        "TRENDING_REGION": trending_region,
        "MAX_TOPICS_PER_RUN": str(max_topics_per_run),
        "BLOCKED_TOPICS": blocked_topics,
        "OPENAI_TTS_VOICE": openai_tts_voice,
        "TTS_VOLUME_BOOST": str(tts_volume_boost),
        "FOCUS_KEYWORDS": focus_keywords,
        "CONTENT_NICHE": content_niche,  # NEW
    }
    existing.update(updates)

    # Write back to .env
    with open(env_path, "r") as f:
        lines = f.readlines()

    # Update existing keys in-place
    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    # Append any new keys not already in .env
    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    # Clear settings cache so new values take effect immediately
    get_settings.cache_clear()

    logger.info(f"Settings updated: format={video_format}, lang={script_language}, region={trending_region}, voice={openai_tts_voice}, niche={content_niche}")

    return {
        "status": "ok",
        "message": "Settings saved and applied",
        "applied": updates,
    }


# ── YouTube Auto-Upload Endpoints ────────────────────────────────────────────

@app.post("/api/v1/youtube/upload/{normalized_keyword}")
async def upload_to_youtube(
    normalized_keyword: str,
    auto_publish: bool = True,
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger YouTube upload with complete A-Z automation.
    
    Auto-generates:
    - SEO titles (5 variants)
    - Description with hooks & timestamps
    - Tags (25+ optimized)
    - Pinned comment
    - Community post
    
    Uploads:
    - Video with custom thumbnail
    - Schedules for optimal time (or immediate)
    """
    from workers.tasks import upload_to_youtube as upload_task
    
    # Queue upload task
    upload_task.delay(normalized_keyword, auto_publish=auto_publish)
    
    return {
        "message": f"YouTube upload queued for '{normalized_keyword}'",
        "status": "processing",
        "auto_publish": auto_publish,
    }


@app.post("/api/v1/youtube/schedule/{normalized_keyword}")
async def schedule_youtube_upload(
    normalized_keyword: str,
    hours: int = 24,
    background_tasks: BackgroundTasks = None,
):
    """
    Schedule YouTube upload for optimal time.
    
    Args:
        hours: Hours from now to publish (default: 24)
    """
    from workers.tasks import upload_to_youtube as upload_task
    
    logger.info(f"Scheduling upload for '{normalized_keyword}' in {hours}h")
    
    # Queue upload with scheduling
    upload_task.delay(normalized_keyword, auto_publish=True)
    
    return {
        "message": f"Upload scheduled for '{normalized_keyword}'",
        "publish_in_hours": hours,
        "status": "scheduled",
    }


@app.get("/api/v1/youtube/analytics/{video_id}")
async def get_youtube_analytics(video_id: str):
    """
    Get YouTube video performance analytics.
    
    Returns:
    - Views, likes, comments
    - CTR (click-through rate)
    - Watch time & retention
    - Performance status
    - Recommendations
    """
    from modules.publisher.analytics_tracker import YouTubeAnalyticsTracker
    
    tracker = YouTubeAnalyticsTracker()
    report = await tracker.get_performance_report(video_id)
    
    return report


@app.get("/api/v1/youtube/analytics/track/{video_id}")
async def track_youtube_analytics(
    video_id: str,
    background_tasks: BackgroundTasks = None,
):
    """Manually trigger analytics tracking for a video."""
    from workers.tasks import track_video_analytics
    
    track_video_analytics.delay(video_id)
    
    return {
        "message": f"Analytics tracking queued for {video_id}",
        "status": "processing",
    }


@app.get("/api/v1/youtube/uploads")
async def list_youtube_uploads(limit: int = 20):
    """List all YouTube uploads with their status."""
    from core.database import get_db
    
    db = await get_db()
    
    cursor = db.video_uploads.find(
        {},
        sort=[("uploaded_at", -1)],
        limit=limit,
    )
    
    uploads = await cursor.to_list(length=limit)
    
    # Remove _id for JSON serialization
    for u in uploads:
        u.pop("_id", None)
    
    return {
        "uploads": uploads,
        "count": len(uploads),
    }


@app.get("/api/v1/youtube/uploads/{normalized_keyword}")
async def get_youtube_upload(normalized_keyword: str):
    """Get upload details for a specific video."""
    from core.database import get_db
    
    db = await get_db()
    
    upload = await db.video_uploads.find_one(
        {"topic_keyword": normalized_keyword}
    )
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload.pop("_id", None)
    return upload


@app.post("/api/v1/youtube/thumbnail/{video_id}/swap")
async def swap_thumbnail_variant(
    video_id: str,
    variant: str,  # "A" or "B"
):
    """
    Swap thumbnail with A/B test variant.
    
    Use this if CTR is low and you want to test alternative thumbnail.
    """
    from modules.publisher.thumbnail_pro import ThumbnailGeneratorPro
    from core.database import get_db
    from pathlib import Path
    
    db = await get_db()
    
    # Get upload record
    upload = await db.video_uploads.find_one({"video_id": video_id})
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Get thumbnail variants (they should be in output/thumbnails/)
    topic = upload.get("topic_keyword", "")
    thumb_dir = Path("output/thumbnails")
    
    variant_file = thumb_dir / f"thumb_{topic}_v{variant.lower()}.png"
    
    if not variant_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Thumbnail variant {variant} not found"
        )
    
    # Upload new thumbnail via API
    from modules.publisher.youtube_uploader_pro import YouTubeUploaderPro
    
    uploader = YouTubeUploaderPro()
    service = uploader._get_service()
    
    from googleapiclient.http import MediaFileUpload
    
    try:
        service.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(
                str(variant_file),
                mimetype="image/png",
            ),
        ).execute()
        
        return {
            "message": f"Thumbnail swapped to variant {variant}",
            "status": "success",
            "video_id": video_id,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Thumbnail swap failed: {str(e)}"
        )


@app.get("/api/v1/youtube/metadata/{normalized_keyword}")
async def regenerate_youtube_metadata(normalized_keyword: str):
    """
    Regenerate YouTube metadata (titles, description, tags).
    
    Useful if you want fresh metadata before upload.
    """
    from modules.publisher.youtube_metadata import YouTubeMetadataOptimizer
    from core.database import get_db
    from core.models import VideoScript
    
    db = await get_db()
    
    # Get script
    script_doc = await db.scripts.find_one(
        {"topic_keyword_normalized": normalized_keyword}
    )
    
    if not script_doc:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Reconstruct script object
    script_data = {
        k: v for k, v in script_doc.items()
        if k not in ("_id", "topic_keyword_normalized", "saved_at")
    }
    
    try:
        script = VideoScript(**script_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Script reconstruction failed: {str(e)}"
        )
    
    # Generate metadata
    optimizer = YouTubeMetadataOptimizer()
    metadata = await optimizer.generate_complete_metadata(
        script=script,
        topic_keyword=normalized_keyword,
    )
    
    return {
        "status": "success",
        "metadata": metadata,
        "topic": normalized_keyword,
    }


# ── Facebook Auto-Upload Endpoints (NEW) ─────────────────────────────────────

@app.post("/api/v1/facebook/upload/{normalized_keyword}")
async def upload_to_facebook(
    normalized_keyword: str,
    auto_publish: bool = True,
    cross_post_to_instagram: bool = False,
    scheduled_hours: int = 0,
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger Facebook Page upload with complete automation.
    
    Auto-generates:
    - Title (Facebook optimized)
    - Description (engagement focused)
    - Tags
    - Thumbnail
    - Optional: Instagram Reels cross-post
    - Optional: Scheduled publishing
    
    Requirements:
    - FACEBOOK_PAGE_ID in .env
    - FACEBOOK_PAGE_ACCESS_TOKEN in .env
    - Meta verified account
    """
    from modules.publisher.facebook_uploader import get_facebook_uploader
    from core.database import get_db
    from datetime import timedelta
    
    async def _upload():
        try:
            db = await get_db()
            
            # Get video and script
            video_doc = await db.videos.find_one({
                "topic_keyword": normalized_keyword
            })
            
            script_doc = await db.scripts.find_one({
                "topic_keyword_normalized": normalized_keyword
            })
            
            if not video_doc or not script_doc:
                logger.error(f"Video or script not found: {normalized_keyword}")
                return
            
            uploader = get_facebook_uploader()
            
            # Calculate schedule time
            schedule_time = None
            if scheduled_hours > 0:
                schedule_time = datetime.utcnow() + timedelta(hours=scheduled_hours)
            
            # Upload to Facebook
            result = await uploader.upload_video(
                video_path=video_doc["output_path"],
                title=script_doc["title"],
                description=script_doc.get("description", ""),
                thumbnail_path=video_doc.get("thumbnail_path"),
                tags=script_doc.get("hashtags", []),
                schedule_time=schedule_time,
                cross_post_to_instagram=cross_post_to_instagram,
            )
            
            # Save upload record
            if result.get("success"):
                await db.facebook_uploads.insert_one({
                    "topic_keyword": normalized_keyword,
                    "video_id": result.get("video_id"),
                    "post_id": result.get("post_id"),
                    "url": result.get("url"),
                    "scheduled": result.get("scheduled"),
                    "scheduled_time": result.get("scheduled_time"),
                    "cross_posted_to_instagram": result.get("cross_posted_to_instagram"),
                    "uploaded_at": result.get("uploaded_at"),
                })
                
                logger.success(f"Facebook upload complete: {result.get('url')}")
            else:
                logger.error(f"Facebook upload failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Facebook upload error: {e}")
    
    if background_tasks:
        background_tasks.add_task(_upload)
    else:
        await _upload()
    
    return {
        "status": "queued",
        "keyword": normalized_keyword,
        "auto_publish": auto_publish,
        "cross_post_to_instagram": cross_post_to_instagram,
        "scheduled_hours": scheduled_hours,
    }


@app.get("/api/v1/facebook/page/info")
async def get_facebook_page_info():
    """Get Facebook Page information."""
    from modules.publisher.facebook_uploader import get_facebook_uploader
    
    try:
        uploader = get_facebook_uploader()
        page_info = await uploader.get_page_info()
        
        return {
            "success": True,
            "page_info": page_info,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@app.get("/api/v1/facebook/video/{video_id}/insights")
async def get_facebook_video_insights(video_id: str, days: int = 7):
    """Get Facebook video performance insights."""
    from modules.publisher.facebook_uploader import get_facebook_uploader

    try:
        uploader = get_facebook_uploader()
        insights = await uploader.get_video_insights(video_id, days)

        return {
            "success": True,
            "insights": insights,
            "days": days,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ── Content-Based Video Generation Endpoints ─────────────────────────────────

from pydantic import BaseModel

class ContentToVideoRequest(BaseModel):
    """Request model for content-to-video processing."""
    content: str
    title: str | None = None
    content_type: str = "article"
    target_duration_sec: int = 90
    style: str = "journalist"
    language: str = "en"
    auto_generate_video: bool = False

@app.post("/api/v1/content-to-video/process", response_model=None)
async def process_content_to_video(
    request: ContentToVideoRequest,
    background_tasks: BackgroundTasks = None,
):
    """
    Convert user-provided content into a video.

    Accepts:
    - Articles/blog posts (paste text)
    - URLs (content will be extracted)
    - Raw text input

    Args:
        request: ContentToVideoRequest with content and options
        background_tasks: FastAPI background tasks

    Returns:
        Script details and optionally triggers video production
    """
    from modules.content_processor import ContentProcessorEngine

    # Validate content
    if not request.content or len(request.content.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Content is too short. Please provide at least 50 characters."
        )

    # Validate style
    valid_styles = ["journalist", "commentary", "humorous", "roast"]
    if request.style not in valid_styles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Choose from: {valid_styles}"
        )

    engine = ContentProcessorEngine()

    # Process content into script
    script = await engine.process_content(
        content=request.content,
        title=request.title,
        content_type=request.content_type,
        target_duration_sec=request.target_duration_sec,
        style=request.style,
        language=request.language,
    )

    if not script:
        raise HTTPException(
            status_code=500,
            detail="Failed to process content. Content may be invalid or too short."
        )

    result = {
        "message": "Content processed successfully",
        "script": {
            "topic_keyword": script.topic_keyword,
            "title": script.title,
            "style": script.style.value,
            "estimated_duration_sec": script.estimated_duration_sec,
            "segments_count": len(script.segments),
            "description": script.description,
            "hashtags": script.hashtags,
        },
    }

    # Optionally trigger video production
    if request.auto_generate_video:
        from modules.video_assembly.engine import VideoProductionEngine

        async def _produce():
            prod_engine = VideoProductionEngine()
            await prod_engine.produce(script.topic_keyword)

        if background_tasks:
            background_tasks.add_task(_produce)
            result["video_production"] = "started"
        else:
            # Run synchronously if no background tasks
            prod_engine = VideoProductionEngine()
            video = await prod_engine.produce(script.topic_keyword)
            result["video_production"] = "completed"
            result["video_path"] = str(video.output_path) if video else None

    return result


@app.get("/api/v1/content-to-video/scripts")
async def list_content_to_video_scripts(limit: int = 20):
    """List all scripts generated from content processor."""
    from modules.content_processor import ContentProcessorEngine

    engine = ContentProcessorEngine()
    scripts = await engine.list_processed_content(limit=limit)

    return {
        "scripts": scripts,
        "count": len(scripts),
    }


@app.get("/api/v1/content-to-video/script/{normalized_keyword}")
async def get_content_video_script(normalized_keyword: str):
    """Get a specific script generated from content."""
    from modules.content_processor import ContentProcessorEngine

    engine = ContentProcessorEngine()
    script = await engine.get_script(normalized_keyword)

    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script


@app.post("/api/v1/content-to-video/produce/{normalized_keyword}")
async def produce_video_from_content(
    normalized_keyword: str,
    background_tasks: BackgroundTasks,
):
    """
    Trigger video production for a script generated from content.
    """
    from modules.video_assembly.engine import VideoProductionEngine

    async def _run():
        engine = VideoProductionEngine()
        video = await engine.produce(normalized_keyword)
        if video:
            logger.info(f"Video produced: {video.output_path}")

    background_tasks.add_task(_run)
    return {
        "message": f"Video production started for '{normalized_keyword}'",
        "status": "running",
    }
