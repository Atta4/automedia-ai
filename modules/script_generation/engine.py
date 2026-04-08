from datetime import datetime
from loguru import logger

from core.models import ContentStyle, TopicStatus, VideoScript
from core.database import get_db
from config.settings import get_settings
from modules.script_generation.generator import ScriptGenerator
from modules.script_generation.niche_prompts import get_niche_system_prompt, get_niche_hook_template
from modules.script_generation.story_prompts import get_story_system_prompt, get_story_hook_template


class ScriptGenerationEngine:
    """
    Orchestrates script generation for validated topics.
    Fetch topic -> generate script -> save -> update status.
    
    NOW WITH NICHE-SPECIFIC PROMPTS:
    - Uses niche from settings (content_niche)
    - Applies niche-specific system prompts
    - Uses niche-appropriate hook templates
    - Customizes tone and structure per niche
    - LONG-FORM for story-based niches (Islamic, History, Horror)
    """

    def __init__(self):
        self.settings = get_settings()
        self.generator = ScriptGenerator()
        self.current_niche = self.settings.content_niche or "current_affairs"
        
        # Niches that need LONG-FORM storytelling
        self.story_niches = ["islamic", "history", "horror_stories", "motivation", "business"]

    async def run_for_topic(
        self,
        normalized_keyword: str,
        style: ContentStyle | None = None,
        niche: str | None = None,  # NEW: Optional niche override
    ) -> VideoScript | None:
        logger.info(f"Script generation: '{normalized_keyword}' (niche: {niche or self.current_niche})")

        topic_doc = await self._load_topic(normalized_keyword)
        if not topic_doc:
            logger.error(f"Topic not found: '{normalized_keyword}'")
            return None

        # Use provided niche or fall back to settings
        target_niche = niche or self.current_niche
        
        # Check if this is a story-based niche
        is_story_niche = target_niche in self.story_niches
        
        # Get appropriate prompts
        if is_story_niche:
            # Use LONG-FORM story prompts
            niche_system_prompt = get_story_system_prompt(target_niche, style.value if style else "journalist")
            hook_templates = get_story_hook_template(target_niche)
            logger.info(f"Using LONG-FORM story prompts for {target_niche}")
        else:
            # Use regular niche prompts
            resolved_style = style or ContentStyle.JOURNALIST
            niche_system_prompt = get_niche_system_prompt(target_niche, resolved_style.value)
            hook_templates = get_niche_hook_template(target_niche)
            logger.info(f"Using standard prompts for {target_niche}")

        try:
            script = await self.generator.generate(
                keyword=topic_doc["keyword"],
                reference_texts=topic_doc.get("youtube_transcripts", []),
                style=style or ContentStyle.JOURNALIST,
                duration_sec=self.settings.target_video_duration,
                niche=target_niche,  # NEW: Pass niche to generator
                system_prompt=niche_system_prompt,  # NEW: Pass niche-specific prompt
                hook_templates=hook_templates,  # NEW: Pass niche-specific hooks
            )
        except Exception as e:
            logger.error(f"Script generation failed for '{normalized_keyword}': {e}")
            await self._update_topic_status(normalized_keyword, TopicStatus.FAILED)
            return None

        await self._save_script(normalized_keyword, script)
        await self._update_topic_status(normalized_keyword, TopicStatus.SCRIPTED)

        logger.success(f"Script saved: '{script.title}' (niche: {target_niche}, story: {is_story_niche})")
        return script

    async def run_batch(
        self,
        limit: int = 5,
        style: ContentStyle | None = None,
    ) -> list[VideoScript]:
        db = await get_db()
        cursor = db.topics.find(
            {"status": TopicStatus.VALIDATED},
            sort=[("total_engagement", -1)],
            limit=limit,
        )
        topics = await cursor.to_list(length=limit)

        if not topics:
            logger.info("No pending topics for script generation")
            return []

        logger.info(f"Batch script generation: {len(topics)} topics")
        scripts: list[VideoScript] = []

        for topic in topics:
            result = await self.run_for_topic(
                normalized_keyword=topic["normalized_keyword"],
                style=style,
            )
            if result:
                scripts.append(result)

        logger.success(f"Batch done: {len(scripts)}/{len(topics)} scripts")
        return scripts

    async def get_script(self, normalized_keyword: str) -> dict | None:
        db = await get_db()
        doc = await db.scripts.find_one({
            "$or": [
                {"topic_keyword_normalized": normalized_keyword},
                {"topic_keyword": normalized_keyword}
            ]
        })
        if doc:
            doc.pop("_id", None)
        return doc

    async def _load_topic(self, normalized_keyword: str) -> dict | None:
        db = await get_db()
        return await db.topics.find_one({"normalized_keyword": normalized_keyword})

    async def _save_script(self, normalized_keyword: str, script: VideoScript) -> None:
        db = await get_db()
        doc = script.model_dump()
        doc["topic_keyword_normalized"] = normalized_keyword
        doc["topic_keyword"] = script.topic_keyword  # Ensure both fields exist
        doc["saved_at"] = datetime.utcnow()
        await db.scripts.update_one(
            {"topic_keyword": normalized_keyword},
            {"$set": doc},
            upsert=True,
        )

    async def _update_topic_status(self, normalized_keyword: str, status: TopicStatus) -> None:
        db = await get_db()
        await db.topics.update_one(
            {"normalized_keyword": normalized_keyword},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        )
