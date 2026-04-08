from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from core.database import get_db
from core.models import TopicStatus


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_NEEDED = "revision_needed"


class ReviewItem(BaseModel):
    normalized_keyword: str
    keyword: str
    video_path: str
    thumbnail_path: Optional[str] = None
    script_title: str
    script_style: str
    duration_sec: float
    file_size_mb: float
    hashtags: list[str] = []
    description: str = ""
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewer_notes: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None


class ReviewQueue:
    """
    Phase 1 manual gate between video assembly and upload.

    Flow:
      assembled → submit_for_review() → PENDING
      Human reviews via API:
        approve()           → queues YouTube upload
        reject()            → marks FAILED
        request_revision()  → resets to VALIDATED, re-queues script
    """

    async def submit_for_review(self, normalized_keyword: str) -> ReviewItem | None:
        db = await get_db()

        video_doc = await db.videos.find_one({"topic_keyword": normalized_keyword})
        if not video_doc:
            logger.error(f"Video not found for review: '{normalized_keyword}'")
            return None

        script_doc = await db.scripts.find_one({"topic_keyword_normalized": normalized_keyword})

        item = ReviewItem(
            normalized_keyword=normalized_keyword,
            keyword=video_doc.get("topic_keyword", normalized_keyword),
            video_path=video_doc.get("output_path", ""),
            thumbnail_path=video_doc.get("thumbnail_path"),
            script_title=script_doc.get("title", "") if script_doc else "",
            script_style=script_doc.get("style", "journalist") if script_doc else "journalist",
            duration_sec=video_doc.get("duration_sec", 0),
            file_size_mb=video_doc.get("file_size_mb", 0),
            hashtags=script_doc.get("hashtags", []) if script_doc else [],
            description=script_doc.get("description", "") if script_doc else "",
        )

        await db.review_queue.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": item.model_dump()},
            upsert=True,
        )
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": TopicStatus.REVIEWED, "updated_at": datetime.utcnow()}},
        )

        logger.success(f"Submitted for review: '{normalized_keyword}'")
        return item

    async def approve(self, normalized_keyword: str, notes: str | None = None) -> dict:
        db = await get_db()
        await db.review_queue.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"review_status": ReviewStatus.APPROVED,
                       "reviewer_notes": notes, "reviewed_at": datetime.utcnow()}},
        )
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": TopicStatus.UPLOADED, "updated_at": datetime.utcnow()}},
        )
        from workers.tasks import upload_to_youtube
        upload_to_youtube.delay(normalized_keyword)
        logger.success(f"APPROVED + upload queued: '{normalized_keyword}'")
        return {"status": "approved", "keyword": normalized_keyword,
                "message": "Approved and queued for YouTube upload"}

    async def reject(self, normalized_keyword: str, notes: str | None = None) -> dict:
        db = await get_db()
        await db.review_queue.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"review_status": ReviewStatus.REJECTED,
                       "reviewer_notes": notes, "reviewed_at": datetime.utcnow()}},
        )
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": TopicStatus.FAILED, "updated_at": datetime.utcnow()}},
        )
        logger.warning(f"REJECTED: '{normalized_keyword}'")
        return {"status": "rejected", "keyword": normalized_keyword,
                "message": "Video rejected"}

    async def request_revision(self, normalized_keyword: str, notes: str | None = None) -> dict:
        db = await get_db()
        await db.review_queue.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"review_status": ReviewStatus.REVISION_NEEDED,
                       "reviewer_notes": notes, "reviewed_at": datetime.utcnow()}},
        )
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": TopicStatus.VALIDATED, "updated_at": datetime.utcnow()}},
        )
        from workers.tasks import generate_script_for_topic
        generate_script_for_topic.delay(normalized_keyword)
        logger.info(f"REVISION requested: '{normalized_keyword}'")
        return {"status": "revision_needed", "keyword": normalized_keyword,
                "message": "Sent back for revision — script will be regenerated"}

    async def get_pending(self, limit: int = 20) -> list[dict]:
        db = await get_db()
        cursor = db.review_queue.find(
            {"review_status": ReviewStatus.PENDING},
            sort=[("submitted_at", -1)], limit=limit,
        )
        items = await cursor.to_list(length=limit)
        for i in items:
            i.pop("_id", None)
        return items

    async def get_item(self, normalized_keyword: str) -> dict | None:
        db = await get_db()
        doc = await db.review_queue.find_one({"normalized_keyword": normalized_keyword})
        if doc:
            doc.pop("_id", None)
        return doc

    async def get_stats(self) -> dict:
        db = await get_db()
        stats = {s.value: await db.review_queue.count_documents({"review_status": s})
                 for s in ReviewStatus}
        stats["total"] = sum(stats.values())
        return stats
