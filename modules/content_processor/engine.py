"""
Content Processor Engine

Analyzes user-provided content and converts it into structured video scripts.
Supports:
- Articles/blog posts
- Raw text input
- URL content extraction
- Key point extraction
- Script structuring for video
"""

import re
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger
from datetime import datetime

from core.models import VideoScript, ScriptSegment, ContentStyle
from config.settings import get_settings


class ContentProcessorEngine:
    """Process user-provided content into video-ready scripts."""

    def __init__(self):
        self.settings = get_settings()
        self.openai_client = None

    def _get_openai_client(self):
        """Lazy-load OpenAI client."""
        if self.openai_client is None:
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self.openai_client

    async def process_content(
        self,
        content: str,
        title: Optional[str] = None,
        content_type: str = "article",
        target_duration_sec: int = 90,
        style: str = "journalist",
        language: str = "en",
    ) -> Optional[VideoScript]:
        """
        Process user-provided content into a video script.

        Args:
            content: The raw content (text, article, blog post)
            title: Optional title for the video
            content_type: Type of content (article, blog, text, url)
            target_duration_sec: Target video duration in seconds
            style: Content style (journalist, commentary, humorous, etc.)
            language: Language code for the content

        Returns:
            VideoScript object ready for video production
        """
        try:
            logger.info(f"Processing content: type={content_type}, style={style}")

            # Step 1: Extract/clean content
            cleaned_content = await self._clean_content(content, content_type)

            if not cleaned_content or len(cleaned_content.strip()) < 50:
                logger.error("Content too short or invalid")
                return None

            # Step 2: Generate normalized keyword from title
            if not title:
                title = await self._generate_title(cleaned_content)

            normalized_keyword = self._normalize_keyword(title)

            # Step 3: Extract key points and structure for video
            script_data = await self._structure_for_video(
                content=cleaned_content,
                title=title,
                target_duration_sec=target_duration_sec,
                style=style,
                language=language,
            )

            if not script_data:
                logger.error("Failed to structure content for video")
                return None

            # Step 4: Create VideoScript object
            script = VideoScript(
                topic_keyword=normalized_keyword,
                title=script_data["title"],
                style=ContentStyle(style),
                segments=[ScriptSegment(**seg) for seg in script_data["segments"]],
                estimated_duration_sec=script_data["estimated_duration_sec"],
                description=script_data.get("description", ""),
                hashtags=script_data.get("hashtags", []),
            )

            # Step 5: Save to database
            await self._save_script(script)

            logger.success(f"Content processed successfully: '{script.title}'")
            return script

        except Exception as e:
            logger.exception(f"Content processing failed: {e}")
            return None

    async def _clean_content(self, content: str, content_type: str) -> str:
        """Clean and extract main content from various formats."""
        try:
            if content_type == "url":
                # Extract content from URL
                content = await self._extract_from_url(content)

            # Remove excessive whitespace
            content = re.sub(r"\n\s*\n", "\n\n", content)
            content = re.sub(r" +", " ", content)

            # Remove common artifacts
            content = re.sub(r"\[.*?\]", "", content)  # Remove [links], [ads], etc.
            content = re.sub(r"Read more.*", "", content, flags=re.IGNORECASE)
            content = re.sub(r"Share this.*", "", content, flags=re.IGNORECASE)

            return content.strip()

        except Exception as e:
            logger.error(f"Content cleaning failed: {e}")
            return content

    async def _extract_from_url(self, url: str) -> str:
        """Extract main content from a URL."""
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")

                # Remove script and style elements
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()

                # Try to find main content
                main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|article|post"))

                if main:
                    text = main.get_text(separator="\n", strip=True)
                else:
                    text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""

                # Clean up text
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                return "\n\n".join(lines)

        except Exception as e:
            logger.error(f"URL extraction failed: {e}")
            return ""

    async def _generate_title(self, content: str) -> str:
        """Generate a title from content using OpenAI."""
        try:
            client = self._get_openai_client()

            prompt = f"""Extract a concise, engaging title (max 60 characters) from this content:

{content[:1000]}...

Return ONLY the title, nothing else."""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert content editor. Extract compelling titles."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=60,
                temperature=0.7,
            )

            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"\'')

            return title if title else "Video Content"

        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return "Video Content"

    def _normalize_keyword(self, title: str) -> str:
        """Convert title to normalized keyword for database storage."""
        # Lowercase and replace spaces with underscores
        keyword = title.lower()
        keyword = re.sub(r"[^\w\s-]", "", keyword)  # Remove special chars
        keyword = re.sub(r"\s+", "_", keyword)  # Replace spaces with underscores
        keyword = keyword[:100]  # Limit length
        return keyword

    async def _structure_for_video(
        self,
        content: str,
        title: str,
        target_duration_sec: int,
        style: str,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        """Structure content into video script format using OpenAI."""
        try:
            client = self._get_openai_client()

            # Calculate target word count (avg 150 words per minute)
            target_words = int((target_duration_sec / 60) * 150)

            style_instructions = {
                "journalist": "Professional, factual, balanced reporting tone",
                "commentary": "Opinionated, analytical, thought-provoking",
                "humorous": "Light-hearted, entertaining, witty",
                "roast": "Sarcastic, bold, comedic criticism",
            }

            prompt = f"""Transform this content into a video script optimized for {target_duration_sec} seconds ({target_words} words max).

CONTENT:
{content[:3000]}...

STYLE: {style_instructions.get(style, style_instructions['journalist'])}

Return a JSON object with this exact structure:
{{
    "title": "Engaging video title",
    "description": "2-3 sentence description",
    "tags": ["tag1", "tag2", "tag3"],
    "hashtags": ["#tag1", "#tag2"],
    "estimated_duration_sec": {target_duration_sec},
    "segments": [
        {{
            "label": "hook",
            "order": 0,
            "text": "Opening hook (first 3-5 seconds)",
            "duration_estimate_sec": 5,
            "visual_cue": "Suggested visual"
        }},
        {{
            "label": "context",
            "order": 1,
            "text": "Main content point 1",
            "duration_estimate_sec": 15,
            "visual_cue": "Suggested visual"
        }}
    ]
}}

Segment labels: hook, context, evidence, analysis, cta

Requirements:
1. Start with a strong hook (first 3-5 seconds)
2. Break content into 3-5 key points
3. End with a strong conclusion and CTA
4. Keep sentences short and punchy for video
5. Add visual cues for each segment

Return ONLY valid JSON, no other text."""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert video script writer. Create engaging, well-structured video scripts."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1500,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            import json
            script_data = json.loads(response.choices[0].message.content)

            # Validate and fix segments
            segments = script_data.get("segments", [])
            for i, seg in enumerate(segments):
                seg["order"] = i
                if "label" not in seg:
                    seg["label"] = "context"
                if "duration_estimate_sec" not in seg:
                    seg["duration_estimate_sec"] = 10

            script_data["segments"] = segments

            return script_data

        except Exception as e:
            logger.exception(f"Video structuring failed: {e}")
            return None

    async def _save_script(self, script: VideoScript) -> None:
        """Save script to MongoDB."""
        from core.database import get_db

        db = await get_db()

        # Use model_dump() to get all VideoScript fields
        doc = script.model_dump()
        
        # Explicitly ensure topic_keyword is set (critical field!)
        doc["topic_keyword"] = script.topic_keyword
        doc["topic_keyword_normalized"] = script.topic_keyword  # For compatibility
        doc["created_at"] = datetime.utcnow().isoformat()
        doc["source"] = "content_processor"  # Mark as from content processor
        doc["saved_at"] = datetime.utcnow()

        # Debug log
        logger.debug(f"Saving script with topic_keyword: {script.topic_keyword}")
        logger.debug(f"Doc keys before save: {list(doc.keys())}")

        await db.scripts.update_one(
            {"topic_keyword": script.topic_keyword},
            {"$set": doc},
            upsert=True,
        )

        logger.info(f"Script saved: {script.topic_keyword}")

    async def get_script(self, keyword: str) -> Optional[Dict[str, Any]]:
        """Retrieve a processed script from database."""
        from core.database import get_db

        db = await get_db()
        script = await db.scripts.find_one(
            {"$or": [{"topic_keyword": keyword}, {"topic_keyword_normalized": keyword}]}
        )

        if script:
            script.pop("_id", None)

        return script

    async def list_processed_content(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List all scripts generated from content processor."""
        from core.database import get_db

        db = await get_db()
        cursor = db.scripts.find(
            {"source": "content_processor"},
            sort=[("created_at", -1)],
            limit=limit,
        )

        scripts = await cursor.to_list(length=limit)
        for s in scripts:
            s.pop("_id", None)

        return scripts
