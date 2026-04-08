import json
import re
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from core.models import ContentStyle, VideoScript, ScriptSegment
from config.settings import get_settings
from modules.script_generation.prompts import (
    SYSTEM_PROMPTS,
    SCRIPT_GENERATION_PROMPT,
    METADATA_PROMPT,
    estimate_word_count,
)


class ScriptGenerator:
    """
    Uses GPT-4o to generate structured video scripts from a trending topic.
    Handles JSON parsing, validation, and retry on malformed output.
    
    NOW SUPPORTS:
    - Niche-specific system prompts
    - Niche-specific hook templates
    - Custom system prompts per niche
    """

    MAX_REFERENCE_CHARS = 3000

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def generate(
        self,
        keyword: str,
        reference_texts: list[str],
        style: ContentStyle = ContentStyle.JOURNALIST,
        duration_sec: int | None = None,
        niche: str | None = None,  # NEW: Optional niche parameter
        system_prompt: str | None = None,  # NEW: Optional custom system prompt
        hook_templates: list[str] | None = None,  # NEW: Optional custom hook templates
    ) -> VideoScript:
        duration_sec = duration_sec or self.settings.target_video_duration
        word_count = estimate_word_count(duration_sec)
        reference_material = self._prepare_reference(reference_texts)

        logger.info(
            f"Generating script | keyword='{keyword}' | style={style} | niche={niche or 'default'} | "
            f"~{word_count} words"
        )

        raw_json = await self._call_gpt(
            keyword=keyword,
            reference_material=reference_material,
            style=style,
            duration_sec=duration_sec,
            word_count=word_count,
            niche=niche,  # NEW
            system_prompt=system_prompt,  # NEW
            hook_templates=hook_templates,  # NEW
        )

        script = self._parse_script(raw_json, keyword, style)
        logger.success(
            f"Script ready: '{script.title}' | "
            f"{len(script.segments)} segments | "
            f"~{script.estimated_duration_sec:.0f}s"
        )
        return script

    async def regenerate_metadata(self, keyword: str, script: VideoScript) -> dict:
        excerpt = script.full_text[:500]
        prompt = METADATA_PROMPT.format(keyword=keyword, script_excerpt=excerpt)

        response = await self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Metadata regeneration returned invalid JSON")
            return {}

    def _prepare_reference(self, texts: list[str]) -> str:
        if not texts:
            return "No reference material available. Generate based on general knowledge."
        parts = []
        budget = self.MAX_REFERENCE_CHARS
        for i, text in enumerate(texts, 1):
            chunk = text[: budget // max(len(texts), 1)]
            parts.append(f"[Source {i}]\n{chunk}")
            budget -= len(chunk)
            if budget <= 0:
                break
        return "\n\n".join(parts)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _call_gpt(
        self,
        keyword: str,
        reference_material: str,
        style: ContentStyle,
        duration_sec: int,
        word_count: int,
        niche: str | None = None,
        system_prompt: str | None = None,
        hook_templates: list[str] | None = None,
    ) -> str:
        # Use custom system prompt if provided, otherwise use default
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            final_system_prompt = SYSTEM_PROMPTS[style]
        
        # Build user prompt with optional niche-specific hooks
        if hook_templates:
            # Add hook guidance to the prompt
            hook_guidance = f"\n\nHOOK GUIDANCE: Use one of these engaging hook styles:\n"
            hook_guidance += "\n".join(f"- {template}" for template in hook_templates[:3])
            hook_guidance += "\n\nMake it sound natural and human-like, not robotic.\n"
        else:
            hook_guidance = ""
        
        user_prompt = SCRIPT_GENERATION_PROMPT.format(
            topic=keyword,
            perspective=style.value,
            reference_material=reference_material,
            style=style.value,
            duration=duration_sec,
            word_count=word_count,
        )
        
        # Add hook guidance if available
        if hook_guidance:
            user_prompt = user_prompt + hook_guidance

        response = await self.client.chat.completions.create(
            model=self.settings.openai_llm_model,
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or ""
        logger.debug(
            f"GPT-4o: prompt={response.usage.prompt_tokens} | "
            f"completion={response.usage.completion_tokens} tokens"
        )
        return content

    def _parse_script(self, raw_json: str, keyword: str, style: ContentStyle) -> VideoScript:
        cleaned = re.sub(r"```(?:json)?|```", "", raw_json).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw: {cleaned[:300]}")
            raise ValueError(f"GPT returned invalid JSON: {e}")

        segments: list[ScriptSegment] = []
        full_text_parts: list[str] = []
        total_duration = 0.0

        for seg_data in data.get("segments", []):
            seg = ScriptSegment(
                order=seg_data.get("order", len(segments) + 1),
                label=seg_data.get("label", "segment"),
                text=seg_data.get("text", ""),
                duration_estimate_sec=float(seg_data.get("duration_estimate_sec", 10)),
                visual_cue=seg_data.get("visual_cue"),
            )
            segments.append(seg)
            full_text_parts.append(seg.text)
            total_duration += seg.duration_estimate_sec

        full_text = " ".join(full_text_parts)

        raw_tags = data.get("hashtags", [])
        hashtags = [
            tag.lstrip("#").replace(" ", "").lower()
            for tag in raw_tags if tag.strip()
        ]

        return VideoScript(
            topic_keyword=keyword,
            style=style,
            title=data.get("title", keyword.title()),
            description=data.get("description", ""),
            hashtags=hashtags,
            segments=segments,
            full_text=full_text,
            estimated_duration_sec=total_duration,
        )
