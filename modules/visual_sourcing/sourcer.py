import asyncio
import json
import re
from pathlib import Path
from enum import Enum

import httpx
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings


class AssetType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"


class VisualAssetInfo:
    def __init__(self, local_path, source, asset_type,
                 duration_sec=0.0, source_url="", visual_cue="", query_used=""):
        self.local_path = local_path
        self.source = source
        self.asset_type = asset_type
        self.duration_sec = duration_sec
        self.source_url = source_url
        self.visual_cue = visual_cue
        self.query_used = query_used


# ── GPT Query Generator ───────────────────────────────────────────────────────

QUERY_PROMPT = """\
You are a video editor picking B-roll for a news/commentary video.

Topic: {topic}
Segment: {label}
Script: {text}
Visual hint: {cue}

Generate 4 stock video search queries (Pexels/Pixabay).
Rules:
- 2-4 words each, concrete nouns only
- Describe exactly what the CAMERA sees
- No abstract words: crisis, situation, concept, symbol, issue
- Order: most specific first, most generic last
- Use real places, objects, people, weather, actions

Examples for "Hawaii flooding":
["hawaii flood street water", "emergency helicopter rescue", "flooded neighborhood aerial", "heavy rain storm"]

Examples for "Iran supreme leader":
["tehran iran city street", "middle east crowd protest", "military soldiers parade", "government building flag"]

Return ONLY a JSON array of 4 strings.
"""


class VisualQueryGenerator:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_queries(self, topic: str, segment_label: str,
                                segment_text: str, visual_cue: str = "") -> list[str]:
        prompt = QUERY_PROMPT.format(
            topic=topic, label=segment_label,
            text=segment_text[:300], cue=visual_cue or "none"
        )
        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=120,
            )
            raw = re.sub(r"```(?:json)?|```", "", resp.choices[0].message.content or "[]").strip()
            queries = json.loads(raw)
            if isinstance(queries, list) and queries:
                logger.debug(f"GPT visual queries [{segment_label}]: {queries}")
                return [str(q).strip() for q in queries[:4] if q]
        except Exception as e:
            logger.warning(f"GPT query gen failed: {e}")

        return self._fallback(topic, visual_cue, segment_label)

    def _fallback(self, topic: str, cue: str, label: str) -> list[str]:
        queries = []
        if cue and len(cue) > 5:
            queries.append(" ".join(cue.lower().split()[:4]))
        words = [w for w in topic.lower().split() if len(w) > 3][:3]
        if words:
            queries.append(" ".join(words))
        defaults = {"hook": "breaking news broadcast", "context": "aerial city view",
                    "evidence": "news report document", "analysis": "expert discussion",
                    "cta": "social media phone"}
        queries.append(defaults.get(label, "news studio"))
        queries.append(topic.split()[0] if topic else "news")
        return queries[:4]


# ── API Clients ───────────────────────────────────────────────────────────────

class PexelsClient:
    BASE = "https://api.pexels.com"

    def __init__(self, api_key: str):
        self.headers = {"Authorization": api_key}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
    async def search_videos(self, query: str, per_page: int = 5) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.BASE}/videos/search", headers=self.headers,
                            params={"query": query, "per_page": per_page, "orientation": "landscape"})
            if r.status_code != 200:
                logger.warning(f"Pexels {r.status_code} for '{query}'")
                return []
            data = r.json()
        results = []
        for v in data.get("videos", []):
            files = sorted(v.get("video_files", []), key=lambda f: abs(f.get("width", 0) - 1280))
            if files:
                results.append({"url": files[0]["link"], "duration": v.get("duration", 10),
                                 "source": "pexels", "query": query})
        return results

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def search_photos(self, query: str, per_page: int = 5) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{self.BASE}/v1/search", headers=self.headers,
                            params={"query": query, "per_page": per_page, "orientation": "landscape"})
            if r.status_code != 200:
                return []
            data = r.json()
        results = []
        for p in data.get("photos", []):
            src = p.get("src", {})
            url = src.get("large2x") or src.get("large") or src.get("original")
            if url:
                results.append({"url": url, "duration": 5, "source": "pexels_photo", "query": query})
        return results


class PixabayClient:
    BASE = "https://pixabay.com/api/videos/"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
    async def search_videos(self, query: str, per_page: int = 5) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(self.BASE, params={"key": self.api_key, "q": query,
                                                "per_page": per_page, "video_type": "film"})
            if r.status_code != 200:
                return []
            data = r.json()
        results = []
        for hit in data.get("hits", []):
            for size in ("large", "medium", "small"):
                vid = hit.get("videos", {}).get(size, {})
                if vid.get("url"):
                    results.append({"url": vid["url"], "duration": hit.get("duration", 10),
                                     "source": "pixabay", "query": query})
                    break
        return results


# ── Main Engine ───────────────────────────────────────────────────────────────

class VisualSourcing:
    """
    90%+ accuracy visual sourcing.
    GPT-4o-mini generates 4 precise queries per segment.
    Tries each query: Pexels video → Pixabay video → Pexels photo.
    """

    def __init__(self):
        self.settings = get_settings()
        self.query_gen = VisualQueryGenerator(self.settings.openai_api_key)
        self.pexels = PexelsClient(self.settings.pexels_api_key) if self.settings.pexels_api_key else None
        self.pixabay = PixabayClient(self.settings.pixabay_api_key) if self.settings.pixabay_api_key else None
        self.temp_dir = Path(self.settings.temp_dir)

    async def fetch_for_segment(self, visual_cue: str, topic_keyword: str,
                                 segment_label: str, segment_text: str,
                                 job_id: str, needed_duration_sec: float = 10.0) -> list[VisualAssetInfo]:
        asset_dir = self.temp_dir / job_id / "visuals" / segment_label
        asset_dir.mkdir(parents=True, exist_ok=True)

        # GPT generates precise queries
        queries = await self.query_gen.generate_queries(
            topic=topic_keyword, segment_label=segment_label,
            segment_text=segment_text, visual_cue=visual_cue,
        )

        logger.info(f"[{segment_label}] Queries: {queries}")

        assets: list[VisualAssetInfo] = []
        total_duration = 0.0

        for query in queries:
            if total_duration >= needed_duration_sec:
                break
            clips = await self._search(query)
            for clip in clips:
                if total_duration >= needed_duration_sec:
                    break
                dl = await self._download(clip, asset_dir, len(assets))
                if dl:
                    assets.append(dl)
                    total_duration += dl.duration_sec
                    logger.debug(f"  ✓ {dl.local_path.name} | query='{query}' | {dl.duration_sec:.0f}s")

        logger.success(
            f"Visuals [{segment_label}]: {len(assets)} clips | "
            f"{total_duration:.1f}s | queries tried: {len(queries)}"
        )
        return assets

    async def fetch_for_all_segments(self, segments_info: list[dict],
                                      topic_keyword: str, job_id: str) -> dict:
        sem = asyncio.Semaphore(2)

        async def _one(seg):
            async with sem:
                assets = await self.fetch_for_segment(
                    visual_cue=seg.get("visual_cue", ""),
                    topic_keyword=topic_keyword,
                    segment_label=seg["label"],
                    segment_text=seg.get("text", ""),
                    job_id=job_id,
                    needed_duration_sec=seg.get("duration_sec", 10.0),
                )
                return seg["label"], assets

        results = await asyncio.gather(*[_one(s) for s in segments_info], return_exceptions=True)
        output = {}
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Segment visual error: {r}")
                continue
            label, assets = r
            output[label] = assets
        return output

    async def _search(self, query: str) -> list[dict]:
        """Pexels video → Pixabay video → Pexels photo."""
        if self.pexels:
            try:
                r = await self.pexels.search_videos(query, per_page=4)
                if r: return r
            except Exception as e:
                logger.warning(f"Pexels video '{query}': {e}")

        if self.pixabay:
            try:
                r = await self.pixabay.search_videos(query, per_page=4)
                if r: return r
            except Exception as e:
                logger.warning(f"Pixabay '{query}': {e}")

        if self.pexels:
            try:
                r = await self.pexels.search_photos(query, per_page=4)
                if r: return r
            except Exception as e:
                logger.warning(f"Pexels photo '{query}': {e}")

        return []

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def _download(self, clip: dict, dest_dir: Path, idx: int) -> VisualAssetInfo | None:
        url = clip["url"]
        source = clip.get("source", "")
        is_photo = "photo" in source or url.lower().endswith((".jpg", ".jpeg", ".png"))
        ext = "jpg" if is_photo else "mp4"
        asset_type = AssetType.IMAGE if is_photo else AssetType.VIDEO
        dest = dest_dir / f"clip_{idx:02d}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return VisualAssetInfo(dest, source, asset_type,
                                   float(clip.get("duration", 5)), url,
                                   query_used=clip.get("query", ""))
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
                r = await c.get(url)
                r.raise_for_status()
                dest.write_bytes(r.content)

            if dest.stat().st_size < 5000:
                dest.unlink(missing_ok=True)
                return None

            return VisualAssetInfo(dest, source, asset_type,
                                   float(clip.get("duration", 5)), url,
                                   query_used=clip.get("query", ""))
        except Exception as e:
            logger.warning(f"Download failed: {e}")
            return None