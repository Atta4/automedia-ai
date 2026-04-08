"""
YouTube Metadata Optimizer for maximum discoverability and CTR.

Generates:
- SEO-optimized titles (multiple variants for A/B testing)
- Description with hooks, timestamps, CTAs
- Tags (mix of broad + specific keywords)
- Hashtags for Shorts/Reels
- Pinned comment templates
- Community post drafts

Uses GPT-4o for intelligent optimization based on:
- Topic trends
- Competitor analysis
- Platform best practices
"""

import json
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from core.models import VideoScript
from config.settings import get_settings


# YouTube SEO best practices
TITLE_MAX_LENGTH = 100  # YouTube displays ~60 chars in search
DESCRIPTION_MAX = 5000  # YouTube limit
TAGS_MAX = 30  # YouTube max tags
HASHTAGS_MAX = 15  # Displayed above title


TITLE_GENERATION_PROMPT = """\
You are a YouTube SEO expert creating viral video titles.

Topic: {topic}
Script Style: {style}
Key Hook: {hook}

Generate 5 title variants following these rules:
1. Under 60 characters (for mobile display)
2. Include primary keyword in first 3 words
3. Use power words: BREAKING, EXCLUSIVE, REVEALED, SHOCKING, URGENT
4. Create curiosity gap (don't give everything away)
5. Avoid clickbait lies (must match content)
6. Add urgency when relevant

Format: JSON array of 5 strings
Example: ["Breaking: X Happens", "Why Y Changed Everything", "The Truth About Z"]

Return ONLY JSON array, no markdown.
"""

DESCRIPTION_PROMPT = """\
You are a YouTube description writer optimizing for SEO and engagement.

Video Topic: {topic}
Full Script: {script_text}
Key Points: {key_points}
Target Duration: {duration}s

Write a YouTube description with this structure:

[HOOK - First 2 lines, visible before "Show More"]
- Grab attention
- Include primary keyword
- Create curiosity

[MAIN BODY - 150-200 words]
- Detailed summary without spoilers
- Include secondary keywords naturally
- Add context and background
- Use short paragraphs (2-3 lines)

[CALL TO ACTION]
- Subscribe prompt
- Related video suggestion
- Social media links placeholder

[TIMESTAMPS]
- Auto-generate from script segments

[HASHTAGS - 5-10 relevant tags]

Return as JSON:
{{
  "hook": "2-line hook",
  "body": "main description",
  "cta": "call to action",
  "timestamps": ["0:00 - Intro", "0:15 - Key point 1"],
  "hashtags": ["#tag1", "#tag2"]
}}
"""

TAGS_GENERATION_PROMPT = """\
You are a YouTube tags expert maximizing discoverability.

Video Topic: {topic}
Primary Keyword: {primary_keyword}
Category: {category}

Generate {count} tags in these categories:

1. PRIMARY (3-5 tags): Exact match keywords
2. BROAD (5-8 tags): General category tags
3. LONG-TAIL (8-12 tags): Specific phrases (3+ words)
4. TRENDING (5-7 tags): Currently trending related terms
5. BRAND (2-3 tags): Channel branding tags

Rules:
- Mix of short (1-2 words) and long (4-6 words) tags
- Include common misspellings/variations
- No irrelevant tags (YouTube penalizes this)
- Prioritize search volume + relevance

Return as JSON array of strings.
Example: ["pakistan news", "imran khan latest", "breaking news pakistan"]
"""

COMMENT_PROMPT = """\
You are a community manager writing engaging pinned comments.

Video Topic: {topic}
Video Angle: {angle}
Target Audience: {audience}

Write 3 pinned comment variants:

1. ENGAGEMENT-FOCUSED: Ask a question to spark discussion
2. VALUE-ADD: Share additional insight/resource
3. CTA-FOCUSED: Drive subscriptions/shares

Each comment should:
- Be conversational and authentic
- Include emoji (2-4, not excessive)
- End with a question or CTA
- Avoid generic "thanks for watching"

Return as JSON:
{{
  "engagement": "comment text",
  "value": "comment text",
  "cta": "comment text"
}}
"""


class YouTubeMetadataOptimizer:
    """
    Generates complete YouTube metadata for maximum reach and engagement.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def generate_complete_metadata(
        self,
        script: VideoScript,
        topic_keyword: str,
        target_audience: str = "general",
    ) -> dict:
        """
        Generate all YouTube metadata in one call.
        
        Returns:
        {
            "titles": [...],  # 5 variants
            "description": {...},
            "tags": [...],
            "hashtags": [...],
            "pinned_comments": {...},
            "category_id": "25",
        }
        """
        logger.info(f"Generating YouTube metadata for: '{topic_keyword}'")

        # Extract key info from script
        hook_segment = next(
            (s for s in script.segments if s.label == "hook"), 
            None
        )
        hook_text = hook_segment.text if hook_segment else script.title

        key_points = " | ".join([
            s.text[:100] for s in script.segments[:3]
        ])

        # Determine category
        category_id = self._infer_category(topic_keyword)

        # Generate all metadata in parallel
        tasks = [
            self.generate_titles(
                topic=topic_keyword,
                style=script.style.value,
                hook=hook_text[:100],
            ),
            self.generate_description(
                topic=topic_keyword,
                script_text=script.full_text,
                key_points=key_points,
                duration=script.estimated_duration_sec,
            ),
            self.generate_tags(
                topic=topic_keyword,
                primary_keyword=topic_keyword,
                category=category_id,
                count=25,
            ),
            self.generate_pinned_comments(
                topic=topic_keyword,
                angle=script.style.value,
                target_audience=target_audience,
            ),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        titles = results[0] if isinstance(results[0], list) else []
        description = results[1] if isinstance(results[1], dict) else {}
        tags = results[2] if isinstance(results[2], list) else []
        comments = results[3] if isinstance(results[3], dict) else {}

        # Extract hashtags from description
        hashtags = description.get("hashtags", [])[:HASHTAGS_MAX]

        metadata = {
            "titles": titles[:5],
            "best_title": titles[0] if titles else script.title,
            "description": description.get("hook", "") + "\n\n" + description.get("body", ""),
            "full_description": self._build_full_description(description),
            "tags": tags[:TAGS_MAX],
            "hashtags": hashtags,
            "pinned_comments": comments,
            "category_id": category_id,
            "timestamps": description.get("timestamps", []),
        }

        logger.success(
            f"Metadata generated: {len(titles)} titles, "
            f"{len(tags)} tags, {len(comments)} comment variants"
        )
        return metadata

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def generate_titles(
        self,
        topic: str,
        style: str,
        hook: str,
    ) -> list[str]:
        """Generate 5 SEO-optimized title variants."""
        prompt = TITLE_GENERATION_PROMPT.format(
            topic=topic,
            style=style,
            hook=hook[:100],
        )

        response = await self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "[]"
        try:
            data = json.loads(raw)
            titles = data if isinstance(data, list) else []
            # Ensure under 100 chars
            return [t[:TITLE_MAX_LENGTH].strip() for t in titles if t]
        except json.JSONDecodeError:
            logger.warning("Title generation returned invalid JSON")
            return [f"Breaking: {topic}"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def generate_description(
        self,
        topic: str,
        script_text: str,
        key_points: str,
        duration: float,
    ) -> dict:
        """Generate complete YouTube description."""
        prompt = DESCRIPTION_PROMPT.format(
            topic=topic,
            script_text=script_text[:1500],  # Truncate for token limit
            key_points=key_points,
            duration=int(duration),
        )

        response = await self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            logger.warning("Description generation returned invalid JSON")
            return {"hook": f"Latest on {topic}", "body": script_text[:500]}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def generate_tags(
        self,
        topic: str,
        primary_keyword: str,
        category: str,
        count: int = 25,
    ) -> list[str]:
        """Generate SEO tags for discoverability."""
        prompt = TAGS_GENERATION_PROMPT.format(
            topic=topic,
            primary_keyword=primary_keyword,
            category=category,
            count=count,
        )

        response = await self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "[]"
        try:
            data = json.loads(raw)
            tags = data if isinstance(data, list) else []
            # Clean tags: lowercase, remove special chars, under 30 chars each
            cleaned = []
            for tag in tags:
                clean_tag = "".join(
                    c for c in tag.lower() 
                    if c.isalnum() or c.isspace()
                )[:30].strip()
                if clean_tag and clean_tag not in cleaned:
                    cleaned.append(clean_tag)
            return cleaned[:count]
        except json.JSONDecodeError:
            logger.warning("Tag generation returned invalid JSON")
            return [primary_keyword, topic]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def generate_pinned_comments(
        self,
        topic: str,
        angle: str,
        target_audience: str,
    ) -> dict:
        """Generate 3 pinned comment variants."""
        prompt = COMMENT_PROMPT.format(
            topic=topic,
            angle=angle,
            target_audience=target_audience,
        )

        response = await self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=400,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            logger.warning("Comment generation returned invalid JSON")
            return {}

    def _infer_category(self, topic: str) -> str:
        """Infer YouTube category ID from topic."""
        topic_lower = topic.lower()
        
        # News & Politics (25)
        if any(word in topic_lower for word in [
            "politics", "government", "election", "prime minister", 
            "president", "parliament", "policy", "law", "bill"
        ]):
            return "25"
        
        # Science & Technology (28)
        if any(word in topic_lower for word in [
            "technology", "science", "ai", "artificial intelligence",
            "space", "research", "discovery"
        ]):
            return "28"
        
        # Education (27)
        if any(word in topic_lower for word in [
            "explained", "tutorial", "guide", "how to", "learn"
        ]):
            return "27"
        
        # Entertainment (24)
        if any(word in topic_lower for word in [
            "celebrity", "movie", "music", "drama", "show"
        ]):
            return "24"
        
        # Default: News & Politics
        return "25"

    def _build_full_description(self, description: dict) -> str:
        """Build complete YouTube description from parts."""
        parts = [
            description.get("hook", ""),
            description.get("body", ""),
            description.get("cta", ""),
        ]
        
        # Add timestamps if available
        timestamps = description.get("timestamps", [])
        if timestamps:
            parts.append("\n⏱️ Timestamps:\n" + "\n".join(timestamps))
        
        # Add hashtags
        hashtags = description.get("hashtags", [])
        if hashtags:
            parts.append("\n" + " ".join(f"#{h}" for h in hashtags[:10]))
        
        full = "\n\n".join(parts)
        return full[:DESCRIPTION_MAX]  # Respect YouTube limit


# Convenience function
async def optimize_for_youtube(
    script: VideoScript,
    topic_keyword: str,
) -> dict:
    """Quick metadata generation."""
    optimizer = YouTubeMetadataOptimizer()
    return await optimizer.generate_complete_metadata(script, topic_keyword)


# Import asyncio for parallel tasks
import asyncio
