import asyncio
import random
from pathlib import Path
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from core.models import ScriptSegment, VideoScript, ContentStyle
from config.settings import get_settings


# ── Voice profiles ────────────────────────────────────────────────────────────
# OpenAI has 6 voices. We define 15 "personas" by combining voice + speed + desc
# so content-based selection feels like different people.

VOICE_PROFILES = [
    # id, openai_voice, speed, description, best_for
    {"id": "anchor_male",     "voice": "onyx",    "speed": 0.95, "desc": "Deep authoritative male anchor",    "styles": ["journalist"]},
    {"id": "anchor_female",   "voice": "nova",    "speed": 0.95, "desc": "Confident female news anchor",      "styles": ["journalist"]},
    {"id": "commentator_m",   "voice": "echo",    "speed": 1.0,  "desc": "Sharp male political commentator",  "styles": ["commentary"]},
    {"id": "commentator_f",   "voice": "shimmer", "speed": 1.0,  "desc": "Energetic female commentator",      "styles": ["commentary"]},
    {"id": "comedian_m",      "voice": "fable",   "speed": 1.05, "desc": "Witty male comedian",               "styles": ["humorous", "roast"]},
    {"id": "comedian_f",      "voice": "alloy",   "speed": 1.05, "desc": "Punchy female comedian",            "styles": ["humorous", "roast"]},
    {"id": "narrator_deep",   "voice": "onyx",    "speed": 0.9,  "desc": "Slow deep documentary narrator",   "styles": ["journalist"]},
    {"id": "narrator_warm",   "voice": "nova",    "speed": 0.92, "desc": "Warm female narrator",              "styles": ["journalist", "commentary"]},
    {"id": "reporter_fast",   "voice": "echo",    "speed": 1.1,  "desc": "Fast-paced breaking news reporter", "styles": ["journalist"]},
    {"id": "pundit_male",     "voice": "onyx",    "speed": 1.0,  "desc": "Calm authoritative pundit",         "styles": ["commentary"]},
    {"id": "pundit_female",   "voice": "shimmer", "speed": 0.98, "desc": "Assertive female pundit",           "styles": ["commentary", "roast"]},
    {"id": "roaster_bold",    "voice": "fable",   "speed": 1.08, "desc": "Bold fearless roaster",             "styles": ["roast"]},
    {"id": "explainer_m",     "voice": "alloy",   "speed": 1.0,  "desc": "Clear male explainer",              "styles": ["journalist", "commentary"]},
    {"id": "explainer_f",     "voice": "nova",    "speed": 1.02, "desc": "Engaging female explainer",         "styles": ["humorous"]},
    {"id": "anchor_neutral",  "voice": "echo",    "speed": 0.97, "desc": "Neutral professional anchor",       "styles": ["journalist", "commentary"]},
]

# Language → voice preference
LANG_VOICE_PREFERENCE = {
    "ur": ["onyx", "echo"],      # deeper voices suit Urdu
    "ar": ["onyx", "fable"],     # Arabic content
    "hi": ["nova", "shimmer"],   # Hindi content
    "en": None,                  # any voice
}


def select_voice(style: str, language: str = "en", voice_setting: str = "auto") -> dict:
    """
    Select best voice profile for content style + language.
    If voice_setting != 'auto', use that specific OpenAI voice directly.
    """
    if voice_setting != "auto":
        # User manually set a voice — find matching profile or create one
        match = next((p for p in VOICE_PROFILES if p["voice"] == voice_setting), None)
        return match or {"id": "custom", "voice": voice_setting, "speed": 1.0,
                         "desc": f"Manual: {voice_setting}", "styles": []}

    # Filter profiles matching the content style
    matching = [p for p in VOICE_PROFILES if style in p.get("styles", [])]
    if not matching:
        matching = VOICE_PROFILES

    # Apply language preference
    lang_pref = LANG_VOICE_PREFERENCE.get(language)
    if lang_pref:
        lang_matching = [p for p in matching if p["voice"] in lang_pref]
        if lang_matching:
            matching = lang_matching

    chosen = random.choice(matching)
    logger.info(f"Voice selected: {chosen['id']} ({chosen['desc']}) | style={style} | lang={language}")
    return chosen


class TTSGenerator:
    """
    Multi-voice TTS with volume boost + content-aware voice selection.
    Supports OpenAI TTS (6 voices → 15 personas) + ElevenLabs (future).
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def generate_and_merge(
        self, script: VideoScript, job_id: str
    ) -> tuple[Path, list[tuple[Path, float]]]:
        """Main entry: generate all segments + merge into final audio."""
        job_dir = Path(self.settings.temp_dir) / job_id / "audio"
        job_dir.mkdir(parents=True, exist_ok=True)

        # Select voice for this script
        voice_profile = select_voice(
            style=script.style.value if script.style else "journalist",
            language=self.settings.script_language,
            voice_setting=self.settings.openai_tts_voice,
        )

        logger.info(
            f"TTS: {len(script.segments)} segments | "
            f"voice={voice_profile['id']} ({voice_profile['voice']}) | "
            f"speed={voice_profile['speed']} | job={job_id}"
        )

        # Generate segments concurrently (max 3 parallel)
        sem = asyncio.Semaphore(3)
        tasks = [
            self._generate_segment(seg, job_dir, sem, voice_profile)
            for seg in sorted(script.segments, key=lambda s: s.order)
        ]
        segment_paths = await asyncio.gather(*tasks)
        valid_paths = [p for p in segment_paths if p is not None]

        if not valid_paths:
            raise ValueError("All TTS segments failed — check OpenAI API key")

        # Get durations
        duration_tasks = [self._get_duration(p) for p in valid_paths]
        durations = await asyncio.gather(*duration_tasks)
        segments_with_duration = list(zip(valid_paths, durations))

        # Merge + boost volume
        merged_path = job_dir / "final_audio.mp3"
        await self._merge_and_boost(valid_paths, merged_path)

        total = sum(durations)
        logger.success(f"Audio ready: {total:.1f}s | voice={voice_profile['id']}")
        return merged_path, segments_with_duration

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def _generate_segment(
        self, segment: ScriptSegment, job_dir: Path,
        sem: asyncio.Semaphore, voice_profile: dict
    ) -> Path | None:
        output_path = job_dir / f"seg_{segment.order:02d}_{segment.label}.mp3"

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        async with sem:
            try:
                logger.debug(f"TTS seg {segment.order} '{segment.label}' | {len(segment.text)} chars")

                response = await self.client.audio.speech.create(
                    model="tts-1-hd",
                    voice=voice_profile["voice"],
                    input=segment.text,
                    response_format="mp3",
                    speed=voice_profile.get("speed", 1.0),
                )

                output_path.write_bytes(response.content)
                logger.debug(f"Seg {segment.order} done: {output_path.stat().st_size/1024:.1f}KB")
                return output_path

            except Exception as e:
                logger.error(f"TTS failed seg {segment.order}: {e}")
                return None

    async def _merge_and_boost(self, paths: list[Path], output: Path) -> None:
        """Merge segments + apply volume boost via FFmpeg."""
        if len(paths) == 1:
            # Still boost single file
            await self._boost_volume(paths[0], output)
            return

        # Concat list
        concat_list = output.parent / "concat.txt"
        with open(concat_list, "w") as f:
            for p in paths:
                f.write(f"file '{p.resolve()}'\n")

        # First concat
        concat_out = output.parent / "concat_raw.mp3"
        cmd_concat = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-acodec", "libmp3lame", "-q:a", "2",
            str(concat_out),
        ]
        await self._run_ffmpeg(cmd_concat)
        concat_list.unlink(missing_ok=True)

        # Then boost volume
        await self._boost_volume(concat_out, output)
        concat_out.unlink(missing_ok=True)

    async def _boost_volume(self, input_path: Path, output_path: Path) -> None:
        """Apply volume boost using FFmpeg loudnorm + volume filter."""
        boost = self.settings.tts_volume_boost
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", f"volume={boost},loudnorm=I=-14:LRA=11:TP=-1.5",
            "-acodec", "libmp3lame", "-q:a", "2",
            str(output_path),
        ]
        await self._run_ffmpeg(cmd)
        logger.debug(f"Volume boosted: {boost}x + loudnorm applied")

    async def _get_duration(self, path: Path) -> float:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "csv=p=0", str(path)]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        try:
            return float(stdout.decode().strip())
        except ValueError:
            return 0.0

    @staticmethod
    async def _run_ffmpeg(cmd: list[str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {stderr.decode()[-400:]}")