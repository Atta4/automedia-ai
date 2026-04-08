import asyncio
import json
from pathlib import Path
from loguru import logger

from modules.visual_sourcing.sourcer import VisualAssetInfo, AssetType
from config.settings import get_settings


# ── Video constants ───────────────────────────────────────────────────────────

OUTPUT_FPS = 30
OUTPUT_CODEC = "libx264"
OUTPUT_AUDIO_CODEC = "aac"
OUTPUT_CRF = 23

def get_dimensions() -> tuple[int, int]:
    from config.settings import get_settings
    return get_settings().get_video_dimensions()


class FFmpegAssembler:
    """
    Assembles final video from:
      - Per-segment visual clips (video or images)
      - Final merged audio track
      - ASS subtitle file (burned into video)

    Pipeline:
      1. Normalize each clip to 1280x720 @ 30fps
      2. Trim/loop clips to match segment audio duration
      3. Concatenate all clips
      4. Mix with audio track
      5. Burn subtitles
      6. Export final MP4
    """

    def __init__(self):
        self.settings = get_settings()
        self.output_dir = Path(self.settings.output_dir)
        self.temp_dir = Path(self.settings.temp_dir)

    # ── Public API ────────────────────────────────────────────────────────────

    async def assemble(
        self,
        job_id: str,
        segment_visuals: dict[str, list[VisualAssetInfo]],
        segment_order: list[dict],
        segment_durations: list[float],
        audio_path: Path,
        subtitle_path: Path,
        output_filename: str,
    ) -> Path:
        """
        Full assembly pipeline.

        segment_visuals:  {label: [VisualAssetInfo]}
        segment_order:    [{"label": str, "order": int}] sorted by order
        segment_durations: real audio durations per segment (same order as segment_order)
        """
        job_dir = self.temp_dir / job_id
        clips_dir = job_dir / "clips_normalized"
        clips_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Video assembly start | job={job_id}")

        # Step 1: Normalize + trim each segment's visuals
        normalized_clips: list[Path] = []
        for seg_info, duration in zip(segment_order, segment_durations):
            label = seg_info["label"]
            visuals = segment_visuals.get(label, [])

            clip = await self._prepare_segment_clip(
                visuals=visuals,
                target_duration=duration,
                output_path=clips_dir / f"seg_{seg_info['order']:02d}_{label}.mp4",
                job_dir=job_dir,
                label=label,
            )
            normalized_clips.append(clip)

        # Step 2: Concatenate all clips
        concat_path = job_dir / "concat_video.mp4"
        await self._concat_clips(normalized_clips, concat_path)

        # Step 3: Mux with audio
        muxed_path = job_dir / "muxed.mp4"
        await self._mux_audio(concat_path, audio_path, muxed_path)

        # Step 4: Burn subtitles
        self.output_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.output_dir / output_filename

        await self._burn_subtitles(muxed_path, subtitle_path, final_path)

        size_mb = final_path.stat().st_size / 1_048_576
        logger.success(
            f"Video assembled: {final_path.name} | {size_mb:.1f}MB"
        )
        return final_path

    async def get_video_duration(self, video_path: Path) -> float:
        """Get video duration using FFprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(video_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        try:
            return float(stdout.decode().strip())
        except ValueError:
            return 0.0

    # ── Private: segment preparation ─────────────────────────────────────────

    async def _prepare_segment_clip(
        self,
        visuals: list[VisualAssetInfo],
        target_duration: float,
        output_path: Path,
        job_dir: Path,
        label: str,
    ) -> Path:
        """
        Normalize visuals for one segment to exactly target_duration seconds.
        If no visuals: generates a black screen placeholder.
        """
        if output_path.exists() and output_path.stat().st_size > 10_000:
            return output_path

        if not visuals:
            logger.warning(f"No visuals for '{label}' — using black placeholder")
            return await self._create_placeholder(target_duration, output_path)

        # Build a sub-clip covering target_duration from available visuals
        sub_clips: list[Path] = []
        accumulated = 0.0
        sub_dir = job_dir / "sub_clips" / label
        sub_dir.mkdir(parents=True, exist_ok=True)

        for i, asset in enumerate(visuals):
            if accumulated >= target_duration:
                break

            needed = target_duration - accumulated
            clip_path = sub_dir / f"sub_{i:02d}.mp4"

            if asset.asset_type == AssetType.VIDEO:
                await self._normalize_video_clip(
                    src=asset.local_path,
                    out=clip_path,
                    duration=min(needed, asset.duration_sec),
                )
                accumulated += min(needed, asset.duration_sec)
            else:
                # Image → slideshow clip
                await self._image_to_video(
                    src=asset.local_path,
                    out=clip_path,
                    duration=min(needed, 5.0),
                )
                accumulated += min(needed, 5.0)

            sub_clips.append(clip_path)

        # If still short, loop last clip
        if accumulated < target_duration - 0.5 and sub_clips:
            loop_clip = sub_dir / "loop.mp4"
            await self._loop_clip(sub_clips[-1], target_duration - accumulated, loop_clip)
            sub_clips.append(loop_clip)

        if len(sub_clips) == 1:
            import shutil
            shutil.copy(sub_clips[0], output_path)
        else:
            await self._concat_clips(sub_clips, output_path)

        return output_path

    async def _normalize_video_clip(
        self, src: Path, out: Path, duration: float
    ) -> None:
        """Scale + trim video clip to 1280x720 @ 30fps."""
        cmd = [
            "ffmpeg", "-y",
            "-ss", "0",
            "-i", str(src),
            "-t", str(duration),
            "-vf", (lambda w,h: f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                   f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
                   f"fps={OUTPUT_FPS}")(*get_dimensions()),
            "-c:v", OUTPUT_CODEC,
            "-crf", str(OUTPUT_CRF),
            "-preset", "fast",
            "-an",           # no audio from clip (we add our own)
            str(out),
        ]
        await self._run_ffmpeg(cmd)

    async def _image_to_video(
        self, src: Path, out: Path, duration: float
    ) -> None:
        """Convert a static image to a video clip with subtle Ken Burns zoom."""
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(src),
            "-t", str(duration),
            "-vf", (lambda w,h: f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                   f"crop={w}:{h},"
                   f"zoompan=z='min(zoom+0.0008,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                   f":d={int(duration * OUTPUT_FPS)}:s={w}x{h},"
                   f"fps={OUTPUT_FPS}")(*get_dimensions()),
            "-c:v", OUTPUT_CODEC,
            "-crf", str(OUTPUT_CRF),
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-an",
            str(out),
        ]
        await self._run_ffmpeg(cmd)

    async def _loop_clip(
        self, src: Path, needed_duration: float, out: Path
    ) -> None:
        """Loop a short clip to fill needed_duration seconds."""
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(src),
            "-t", str(needed_duration),
            "-c", "copy",
            str(out),
        ]
        await self._run_ffmpeg(cmd)

    async def _create_placeholder(
        self, duration: float, out: Path
    ) -> Path:
        """Create a black screen video for segments with no visuals."""
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", (lambda w,h: f"color=c=black:size={w}x{h}:rate={OUTPUT_FPS}")(*get_dimensions()),
            "-t", str(duration),
            "-c:v", OUTPUT_CODEC,
            "-crf", str(OUTPUT_CRF),
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(out),
        ]
        await self._run_ffmpeg(cmd)
        return out

    # ── Private: concat + mux + subtitles ────────────────────────────────────

    async def _concat_clips(
        self, clip_paths: list[Path], output_path: Path
    ) -> None:
        """Concatenate video clips using FFmpeg concat demuxer."""
        concat_list = output_path.parent / f"concat_{output_path.stem}.txt"
        with open(concat_list, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(output_path),
        ]
        await self._run_ffmpeg(cmd)
        concat_list.unlink(missing_ok=True)

    async def _mux_audio(
        self, video_path: Path, audio_path: Path, output_path: Path
    ) -> None:
        """Combine video track with audio track. Trim to shortest."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", OUTPUT_AUDIO_CODEC,
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]
        await self._run_ffmpeg(cmd)

    async def _burn_subtitles(
        self, video_path: Path, subtitle_path: Path, output_path: Path
    ) -> None:
        """Burn ASS/SRT subtitles directly into video pixels."""
        # Escape path for FFmpeg filter (Windows paths need special handling)
        sub_str = str(subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")

        if subtitle_path.suffix == ".ass":
            sub_filter = f"ass='{sub_str}'"
        else:
            sub_filter = (
                f"subtitles='{sub_str}':force_style='"
                "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,Outline=2,Shadow=1,"
                "Alignment=2,MarginV=25'"
            )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", sub_filter,
            "-c:v", OUTPUT_CODEC,
            "-crf", str(OUTPUT_CRF),
            "-preset", "fast",
            "-c:a", "copy",
            str(output_path),
        ]
        await self._run_ffmpeg(cmd)

    # ── FFmpeg runner ─────────────────────────────────────────────────────────

    @staticmethod
    async def _run_ffmpeg(cmd: list[str]) -> None:
        logger.debug(f"FFmpeg: {' '.join(cmd[:6])}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode()[-600:]
            raise RuntimeError(f"FFmpeg failed (code {proc.returncode}):\n{err}")