import re
import asyncio
from datetime import datetime
from pathlib import Path
from loguru import logger

from core.models import TopicStatus, FinalVideo, VideoScript
from core.database import get_db
from config.settings import get_settings
from modules.tts.generator import TTSGenerator
from modules.visual_sourcing.sourcer import VisualSourcing
from modules.video_assembly.assembler import FFmpegAssembler
from modules.video_assembly.subtitle_generator import generate_ass_subtitles
from modules.thumbnail.generator import ThumbnailGenerator
from modules.publisher.review_queue import ReviewQueue


def _safe_filename(text: str, max_len: int = 50) -> str:
    safe = re.sub(r"[^\w\s-]", "", text.lower())
    safe = re.sub(r"[\s_-]+", "_", safe).strip("_")
    return safe[:max_len]


class VideoProductionEngine:
    """
    Full pipeline for one topic:
      TTS audio → visuals → subtitles → FFmpeg MP4
      → thumbnail → review queue submission
    """

    def __init__(self):
        self.settings = get_settings()
        self.tts = TTSGenerator()
        self.visuals = VisualSourcing()
        self.assembler = FFmpegAssembler()
        self.thumbnail_gen = ThumbnailGenerator()
        self.review_queue = ReviewQueue()

    async def produce(self, normalized_keyword: str) -> FinalVideo | None:
        logger.info(f"=== Video Production START: '{normalized_keyword}' ===")

        script = await self._load_script(normalized_keyword)
        if not script:
            logger.error(f"No script found: '{normalized_keyword}'")
            return None

        job_id = _safe_filename(normalized_keyword)

        try:
            # Step 1: TTS
            logger.info("Step 1/5: Generating TTS audio...")
            merged_audio, segments_with_duration = await self.tts.generate_and_merge(
                script=script, job_id=job_id
            )
            segment_durations = [d for _, d in segments_with_duration]
            logger.info(f"Audio: {sum(segment_durations):.1f}s total")

            # Step 2: Visuals
            logger.info("Step 2/5: Fetching visuals...")
            segments_info = [
                {
                    "label": seg.label,
                    "order": seg.order,
                    "visual_cue": seg.visual_cue or "",
                    "text": seg.text,
                    "duration_sec": segment_durations[i] if i < len(segment_durations) else 10.0,
                }
                for i, seg in enumerate(sorted(script.segments, key=lambda s: s.order))
            ]
            segment_visuals = await self.visuals.fetch_for_all_segments(
                segments_info=segments_info,
                topic_keyword=script.topic_keyword,
                job_id=job_id,
            )

            # Step 3: Subtitles
            logger.info("Step 3/5: Generating subtitles...")
            temp_dir = Path(self.settings.temp_dir) / job_id
            subtitle_path = temp_dir / "subtitles.ass"
            generate_ass_subtitles(
                segments=[{"label": s.label, "text": s.text, "order": s.order}
                           for s in sorted(script.segments, key=lambda s: s.order)],
                segment_durations=segment_durations,
                output_path=subtitle_path,
                style="modern",
            )

            # Step 4: Assemble video
            logger.info("Step 4/5: Assembling video...")
            output_filename = f"{job_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4"
            final_path = await self.assembler.assemble(
                job_id=job_id,
                segment_visuals=segment_visuals,
                segment_order=sorted(segments_info, key=lambda s: s["order"]),
                segment_durations=segment_durations,
                audio_path=merged_audio,
                subtitle_path=subtitle_path,
                output_filename=output_filename,
            )

            # Step 5: Thumbnail
            logger.info("Step 5/5: Generating thumbnail...")
            thumbnail_path_str = None
            try:
                thumb_path = await self.thumbnail_gen.generate(
                    title=script.title,
                    topic_keyword=script.topic_keyword,
                    style=script.style.value,
                    job_id=job_id,
                )
                thumbnail_path_str = str(thumb_path)
            except Exception as e:
                logger.warning(f"Thumbnail failed (non-fatal): {e}")

            # Build + save FinalVideo
            size_mb = final_path.stat().st_size / 1_048_576
            video_duration = await self.assembler.get_video_duration(final_path)

            final_video = FinalVideo(
                topic_keyword=normalized_keyword,
                output_path=str(final_path),
                thumbnail_path=thumbnail_path_str,
                duration_sec=video_duration,
                file_size_mb=round(size_mb, 2),
                script=script,
                status=TopicStatus.ASSEMBLED,
            )

            await self._save_final_video(final_video)
            await self._update_topic_status(normalized_keyword, TopicStatus.ASSEMBLED)

            # Auto-submit to review queue
            await self.review_queue.submit_for_review(normalized_keyword)

            logger.success(
                f"=== DONE & IN REVIEW QUEUE: {final_path.name} | "
                f"{video_duration:.1f}s | {size_mb:.1f}MB ==="
            )
            return final_video

        except Exception as e:
            logger.exception(f"Production failed '{normalized_keyword}': {e}")
            await self._update_topic_status(normalized_keyword, TopicStatus.FAILED)
            return None

    async def produce_batch(self, limit: int = 3) -> list[FinalVideo]:
        db = await get_db()
        cursor = db.topics.find(
            {"status": TopicStatus.SCRIPTED},
            sort=[("total_engagement", -1)], limit=limit,
        )
        topics = await cursor.to_list(length=limit)
        if not topics:
            logger.info("No scripted topics ready for production")
            return []
        logger.info(f"Batch production: {len(topics)} topics")
        results = []
        for topic in topics:
            video = await self.produce(topic["normalized_keyword"])
            if video:
                results.append(video)
        logger.success(f"Batch done: {len(results)}/{len(topics)} videos")
        return results

    async def _load_script(self, normalized_keyword: str) -> VideoScript | None:
        db = await get_db()
        # Try both field names for compatibility
        doc = await db.scripts.find_one({
            "$or": [
                {"topic_keyword_normalized": normalized_keyword},
                {"topic_keyword": normalized_keyword}
            ]
        })
        if not doc:
            logger.error(f"Script not found in database: {normalized_keyword}")
            return None
        
        logger.debug(f"Loaded script from DB, keys: {list(doc.keys())}")
        
        # Remove MongoDB and metadata fields only
        doc.pop("_id", None)
        doc.pop("saved_at", None)
        doc.pop("source", None)
        doc.pop("created_at", None)
        doc.pop("updated_at", None)
        
        # If topic_keyword is missing but topic_keyword_normalized exists, use it
        if "topic_keyword" not in doc and "topic_keyword_normalized" in doc:
            doc["topic_keyword"] = doc["topic_keyword_normalized"]
            logger.debug(f"Using topic_keyword_normalized as topic_keyword: {doc['topic_keyword']}")
        
        logger.debug(f"After cleanup, keys: {list(doc.keys())}")
        logger.debug(f"topic_keyword value: {doc.get('topic_keyword', 'MISSING')}")
            
        try:
            return VideoScript(**doc)
        except Exception as e:
            logger.error(f"Script parse error: {e}")
            logger.error(f"Doc keys: {list(doc.keys())}")
            logger.error(f"Missing topic_keyword: {'topic_keyword' not in doc}")
            return None

    async def _save_final_video(self, video: FinalVideo) -> None:
        db = await get_db()
        doc = video.model_dump()
        doc["script"] = video.script.model_dump() if video.script else None
        await db.videos.update_one(
            {"topic_keyword": video.topic_keyword},
            {"$set": doc}, upsert=True,
        )

    async def _update_topic_status(self, normalized_keyword: str, status: TopicStatus) -> None:
        db = await get_db()
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        )