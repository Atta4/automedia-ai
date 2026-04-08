import sys
import os
from pathlib import Path

# Add project root to Python path for Celery worker
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '')
os.environ.setdefault('PYTHONPATH', str(project_root))

import asyncio
from celery import Celery
from loguru import logger
from config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "automedia",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "collect-trending-topics": {
            "task": "workers.tasks.collect_trending_topics",
            "schedule": 7200.0,
        },
    },
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Task 1: Data Collection ───────────────────────────────────────────────────

@celery_app.task(name="workers.tasks.collect_trending_topics", bind=True, max_retries=3)
def collect_trending_topics(self):
    """Discover + validate trending topics, then queue script generation."""
    from modules.data_collection.engine import DataCollectionEngine

    logger.info(f"[{self.request.id}] collect_trending_topics: START")

    async def _run():
        engine = DataCollectionEngine()
        validated_topics = await engine.run()
        for topic in validated_topics:
            generate_script_for_topic.delay(topic.normalized_keyword)
            logger.info(f"Queued script gen: '{topic.keyword}'")
        return len(validated_topics)

    try:
        count = _run_async(_run())
        logger.success(f"[{self.request.id}] DONE — {count} topics queued")
        return {"status": "success", "topics_queued": count}
    except Exception as exc:
        logger.error(f"[{self.request.id}] FAILED: {exc}")
        raise self.retry(exc=exc, countdown=60)


# ── Task 2: Script Generation ─────────────────────────────────────────────────

@celery_app.task(name="workers.tasks.generate_script_for_topic", bind=True, max_retries=2)
def generate_script_for_topic(self, normalized_keyword: str, style: str | None = None):
    """Generate GPT-4o script for a validated topic, then queue TTS."""
    from modules.script_generation.engine import ScriptGenerationEngine
    from modules.script_generation.style_selector import auto_select_style
    from core.models import ContentStyle

    logger.info(f"[{self.request.id}] generate_script: '{normalized_keyword}'")

    async def _run():
        engine = ScriptGenerationEngine()

        # Use provided style or auto-select based on keyword
        resolved_style = (
            ContentStyle(style) if style
            else auto_select_style(normalized_keyword)
        )

        script = await engine.run_for_topic(
            normalized_keyword=normalized_keyword,
            style=resolved_style,
        )

        if script:
            # Queue TTS generation (Module 3)
            generate_tts_for_script.delay(normalized_keyword)
            logger.info(f"Queued TTS: '{normalized_keyword}'")
            return {"status": "success", "title": script.title}

        return {"status": "failed", "keyword": normalized_keyword}

    try:
        result = _run_async(_run())
        logger.success(f"[{self.request.id}] Script done: {result}")
        return result
    except Exception as exc:
        logger.error(f"[{self.request.id}] Script FAILED: {exc}")
        raise self.retry(exc=exc, countdown=30)


# ── Task 3: TTS (placeholder — Module 3 will implement) ──────────────────────

@celery_app.task(name="workers.tasks.generate_tts_for_script", bind=True, max_retries=2)
def generate_tts_for_script(self, normalized_keyword: str):
    """Triggers full video production (TTS + visuals + assembly)."""
    logger.info(f"[{self.request.id}] Triggering video production: '{normalized_keyword}'")
    produce_video.delay(normalized_keyword)
    return {"status": "queued", "keyword": normalized_keyword}


# ── Task 3: Video Production (TTS + Visuals + Assembly) ──────────────────────

@celery_app.task(name="workers.tasks.produce_video", bind=True, max_retries=2)
def produce_video(self, normalized_keyword: str):
    """
    Full video production for a scripted topic:
    TTS → Visuals → Subtitles → FFmpeg assembly → DB save
    """
    from modules.video_assembly.engine import VideoProductionEngine

    logger.info(f"[{self.request.id}] produce_video: '{normalized_keyword}'")

    async def _run():
        engine = VideoProductionEngine()
        video = await engine.produce(normalized_keyword)
        if video:
            return {
                "status": "success",
                "output": video.output_path,
                "duration_sec": video.duration_sec,
                "size_mb": video.file_size_mb,
            }
        return {"status": "failed", "keyword": normalized_keyword}

    try:
        result = _run_async(_run())
        logger.success(f"[{self.request.id}] Video done: {result}")
        return result
    except Exception as exc:
        logger.error(f"[{self.request.id}] Video FAILED: {exc}")
        raise self.retry(exc=exc, countdown=60)


# ── Task 4: YouTube Upload ────────────────────────────────────────────────────

@celery_app.task(name="workers.tasks.upload_to_youtube", bind=True, max_retries=2)
def upload_to_youtube(self, normalized_keyword: str, **kwargs):
    """
    Upload an approved video to YouTube with complete A-Z automation.
    
    ALWAYS UPLOADS PUBLICLY IMMEDIATELY with:
    - SEO optimized title, description, tags
    - Hashtags in description
    - Source URLs in description
    - Thumbnail upload
    - Pinned comment

    Args:
        normalized_keyword: Topic keyword
    """
    import sys
    from pathlib import Path

    # Ensure project root is in Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from modules.publisher.youtube_uploader_pro import YouTubeUploaderPro
    from modules.publisher.youtube_metadata import YouTubeMetadataOptimizer

    logger.info(f"[{self.request.id}] Auto YouTube upload: '{normalized_keyword}'")

    async def _run():
        db_module = __import__("core.database", fromlist=["get_db"])
        db = await db_module.get_db()

        # Fetch video and script
        video_doc = await db.videos.find_one({"topic_keyword": normalized_keyword})
        script_doc = await db.scripts.find_one({"topic_keyword_normalized": normalized_keyword})

        if not video_doc:
            return {"status": "error", "message": "Video record not found"}

        if not script_doc:
            logger.warning(f"No script for '{normalized_keyword}', generating basic metadata")
            script_doc = {}

        # Reconstruct VideoScript object for metadata generation
        from core.models import VideoScript, ContentStyle, ScriptSegment

        try:
            script_data = {k: v for k, v in script_doc.items()
                          if k not in ("_id", "topic_keyword_normalized", "saved_at")}
            script = VideoScript(**script_data)
        except Exception as e:
            logger.warning(f"Script reconstruction failed: {e}")
            script = None

        # Step 1: Generate complete metadata WITH SOURCES
        logger.info("Step 1: Generating SEO metadata with sources...")
        metadata_optimizer = YouTubeMetadataOptimizer()

        if script:
            metadata = await metadata_optimizer.generate_complete_metadata(
                script=script,
                topic_keyword=normalized_keyword,
            )
            
            # Add source URLs to description
            topic_doc = await db.topics.find_one({"normalized_keyword": normalized_keyword})
            if topic_doc and "sources" in topic_doc:
                sources = topic_doc["sources"][:5]  # Top 5 sources
                source_urls = [s.get("url") for s in sources if s.get("url")]
                
                if source_urls:
                    # Append sources to description
                    sources_section = "\n\n📚 Sources:\n" + "\n".join(source_urls)
                    metadata["description"] = metadata.get("description", "") + sources_section
                    metadata["full_description"] = metadata.get("full_description", "") + sources_section
                    
                    logger.info(f"Added {len(source_urls)} source URLs to description")
        else:
            # Fallback basic metadata
            metadata = {
                "best_title": script_doc.get("title", normalized_keyword),
                "description": script_doc.get("description", ""),
                "tags": [t.strip() for t in normalized_keyword.split(",")],
                "hashtags": script_doc.get("hashtags", []),
                "category_id": "25",
                "pinned_comments": {},
            }

        logger.info(f"Metadata generated: {metadata.get('best_title', 'N/A')}")

        # Step 2: Upload PUBLICLY immediately (no scheduling)
        logger.info("Step 2: Uploading to YouTube as PUBLIC...")
        uploader = YouTubeUploaderPro()

        video_path = Path(video_doc["output_path"])
        thumbnail_path = Path(video_doc["thumbnail_path"]) if video_doc.get("thumbnail_path") else None

        try:
            # ALWAYS upload as PUBLIC immediately
            result = await uploader.upload_complete(
                video_path=video_path,
                metadata=metadata,
                thumbnail_path=thumbnail_path,
                auto_publish=True,  # Public immediately
            )

            # Step 3: Update database
            if result.get("status") == "success":
                await db.videos.update_one(
                    {"topic_keyword": normalized_keyword},
                    {
                        "$set": {
                            "youtube_url": result["url"],
                            "youtube_id": result["video_id"],
                            "youtube_privacy": result.get("privacy", "public"),
                            "youtube_scheduled": result.get("scheduled_for"),
                            "youtube_thumbnail": result.get("thumbnail_uploaded", False),
                            "youtube_comment_id": result.get("pinned_comment_id"),
                            "youtube_community_post": result.get("community_post_id"),
                            "status": "uploaded",
                        }
                    },
                )
                
                # Save metadata for reference
                await db.video_uploads.update_one(
                    {"video_id": result["video_id"]},
                    {"$set": {
                        "topic_keyword": normalized_keyword,
                        "metadata": metadata,
                        "upload_result": result,
                    }},
                    upsert=True,
                )
                
                logger.success(
                    f"✓ Upload complete: {result['url']} | "
                    f"Scheduled: {result.get('scheduled_for', 'Immediate')} | "
                    f"Community Post: {result.get('community_post_id', 'N/A')}"
                )
            else:
                logger.error(f"Upload failed: {result.get('message', 'Unknown error')}")

            return result
            
        except Exception as e:
            logger.exception(f"YouTube upload error: {e}")
            return {"status": "error", "message": str(e)}

    try:
        # Properly handle async execution in Celery worker
        import nest_asyncio
        try:
            nest_asyncio.apply()
        except Exception:
            pass

        # Check if there's an existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_run())
        logger.success(f"[{self.request.id}] Upload complete: {result}")
        return result
    except Exception as exc:
        logger.error(f"[{self.request.id}] Upload FAILED: {exc}")
        raise self.retry(exc=exc, countdown=120)


# ── Task 5: Analytics Tracking ────────────────────────────────────────────────

@celery_app.task(name="workers.tasks.track_video_analytics", bind=True, max_retries=3)
def track_video_analytics(self, video_id: str):
    """
    Track YouTube video analytics and save to database.
    Runs daily for uploaded videos.
    """
    from modules.publisher.analytics_tracker import YouTubeAnalyticsTracker

    logger.info(f"[{self.request.id}] Tracking analytics for: {video_id}")

    async def _run():
        tracker = YouTubeAnalyticsTracker()
        
        # Get performance report
        report = await tracker.get_performance_report(video_id)
        
        # Save to database
        db_module = __import__("core.database", fromlist=["get_db"])
        db = await db_module.get_db()
        
        await db.video_analytics.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "latest_report": report,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            },
            upsert=True,
        )
        
        # Log key metrics
        metrics = report.get("metrics", {})
        logger.info(
            f"[{video_id}] Views: {metrics.get('views', 0)} | "
            f"CTR: {metrics.get('ctr', 0)}% | "
            f"Watch Time: {metrics.get('watch_time_hours', 0)}h"
        )
        
        return report

    try:
        result = _run_async(_run())
        logger.success(f"[{self.request.id}] Analytics tracked")
        return result
    except Exception as exc:
        logger.error(f"[{self.request.id}] Analytics failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


# ── Task 6: Content-to-Video Processing ──────────────────────────────────────

@celery_app.task(name="workers.tasks.process_content_to_video", bind=True, max_retries=2)
def process_content_to_video(
    self,
    content: str,
    title: str | None = None,
    content_type: str = "article",
    target_duration_sec: int = 90,
    style: str = "journalist",
    language: str = "en",
    auto_generate_video: bool = False,
):
    """
    Process user-provided content into a video script.

    This task:
    1. Analyzes the provided content
    2. Extracts key points
    3. Structures it into a video script
    4. Optionally triggers video production
    """
    from modules.content_processor import ContentProcessorEngine

    logger.info(f"[{self.request.id}] Processing content: type={content_type}, style={style}")

    async def _run():
        engine = ContentProcessorEngine()

        # Process content into script
        script = await engine.process_content(
            content=content,
            title=title,
            content_type=content_type,
            target_duration_sec=target_duration_sec,
            style=style,
            language=language,
        )

        if not script:
            return {"status": "failed", "error": "Failed to process content"}

        result = {
            "status": "success",
            "topic_keyword": script.topic_keyword_normalized,
            "title": script.title,
            "style": script.style.value,
            "estimated_duration_sec": script.estimated_duration_sec,
            "segments_count": len(script.segments),
        }

        # Optionally trigger video production
        if auto_generate_video:
            logger.info(f"Auto-generating video for: {script.topic_keyword_normalized}")
            produce_video.delay(script.topic_keyword_normalized)
            result["video_production"] = "queued"

        return result

    try:
        result = _run_async(_run())
        logger.success(f"[{self.request.id}] Content processed: {result.get('title', 'N/A')}")
        return result
    except Exception as exc:
        logger.error(f"[{self.request.id}] Content processing FAILED: {exc}")
        raise self.retry(exc=exc, countdown=60)


# Import datetime for analytics task
from datetime import datetime
