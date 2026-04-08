import asyncio
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from loguru import logger

from config.settings import get_settings

THUMB_W = 1280
THUMB_H = 720

STYLE_PRESETS = {
    "journalist": {
        "bg_top": (15, 15, 25), "bg_bottom": (30, 30, 50),
        "accent": (220, 50, 50), "title_color": (255, 255, 255),
        "label_text": "BREAKING", "label_bg": (220, 50, 50),
    },
    "commentary": {
        "bg_top": (10, 20, 40), "bg_bottom": (20, 40, 80),
        "accent": (50, 150, 255), "title_color": (255, 255, 255),
        "label_text": "ANALYSIS", "label_bg": (50, 150, 255),
    },
    "humorous": {
        "bg_top": (40, 10, 60), "bg_bottom": (80, 20, 100),
        "accent": (255, 200, 0), "title_color": (255, 255, 255),
        "label_text": "VIRAL", "label_bg": (255, 180, 0),
    },
    "roast": {
        "bg_top": (30, 10, 10), "bg_bottom": (60, 15, 15),
        "accent": (255, 80, 0), "title_color": (255, 255, 255),
        "label_text": "HOT TAKE", "label_bg": (255, 80, 0),
    },
}


class ThumbnailGenerator:
    """
    Generates YouTube-style thumbnails (1280x720) using Pillow.
    Layout: gradient bg → blurred image → accent bar → badge → title → keyword pill
    """

    def __init__(self):
        self.settings = get_settings()
        self.output_dir = Path(self.settings.output_dir)

    async def generate(
        self,
        title: str,
        topic_keyword: str,
        style: str = "journalist",
        background_image_path: Path | None = None,
        thumbnail_text: str | None = None,
        job_id: str | None = None,
    ) -> Path:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._render, title, topic_keyword,
            style, background_image_path, thumbnail_text, job_id,
        )

    def _render(self, title, topic_keyword, style, bg_image_path, thumbnail_text, job_id) -> Path:
        preset = STYLE_PRESETS.get(style, STYLE_PRESETS["journalist"])
        img = Image.new("RGB", (THUMB_W, THUMB_H), preset["bg_top"])

        self._draw_gradient(img, preset["bg_top"], preset["bg_bottom"])

        if bg_image_path and Path(bg_image_path).exists():
            self._apply_bg_image(img, Path(bg_image_path))

        draw = ImageDraw.Draw(img)

        # Left accent bar
        draw.rectangle([(0, 0), (12, THUMB_H)], fill=preset["accent"])

        # Top badge
        self._draw_label_badge(draw, preset)

        # Main title
        display_title = thumbnail_text if thumbnail_text else title
        self._draw_title(draw, display_title, preset)

        # Keyword pill
        self._draw_keyword_pill(draw, topic_keyword, preset)

        # Bottom color strip
        self._draw_bottom_strip(img, preset)

        out_dir = self.output_dir / "thumbnails"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in topic_keyword)[:40]
        suffix = f"_{job_id}" if job_id else ""
        out_path = out_dir / f"thumb_{safe}{suffix}.png"
        img.save(out_path, "PNG", optimize=True)
        logger.success(f"Thumbnail: {out_path.name}")
        return out_path

    def _draw_gradient(self, img, top, bottom):
        draw = ImageDraw.Draw(img)
        for y in range(THUMB_H):
            r = top[0] + int((bottom[0] - top[0]) * y / THUMB_H)
            g = top[1] + int((bottom[1] - top[1]) * y / THUMB_H)
            b = top[2] + int((bottom[2] - top[2]) * y / THUMB_H)
            draw.line([(0, y), (THUMB_W, y)], fill=(r, g, b))

    def _apply_bg_image(self, img, path):
        try:
            bg = Image.open(path).convert("RGB").resize((THUMB_W, THUMB_H), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=12))
            bg = ImageEnhance.Brightness(bg).enhance(0.35)
            img.paste(bg, (0, 0))
        except Exception as e:
            logger.warning(f"BG image error: {e}")

    def _draw_label_badge(self, draw, preset):
        label = preset["label_text"]
        font = self._get_font(20, bold=True)
        bx, by, pad = 28, 28, 18
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rectangle([(bx, by), (bx + tw + pad * 2, by + th + 20)], fill=preset["label_bg"])
        draw.text((bx + pad, by + 10), label, font=font, fill=(255, 255, 255))

    def _draw_title(self, draw, title, preset):
        for font_size in [88, 72, 60, 50, 42]:
            font = self._get_font(font_size, bold=True)
            wrapped = textwrap.fill(title, width=max(10, int(900 / (font_size * 0.55))))
            lines = wrapped.split("\n")
            line_heights = [draw.textbbox((0, 0), l, font=font)[3] for l in lines]
            total_h = sum(line_heights) + (len(lines) - 1) * 16
            if total_h < THUMB_H * 0.65 or font_size == 42:
                break

        y = int(THUMB_H * 0.28)
        for i, line in enumerate(lines):
            lh = line_heights[i]
            cur_y = y + sum(line_heights[:i]) + i * 16
            draw.text((63, cur_y + 3), line, font=font, fill=(0, 0, 0))
            draw.text((60, cur_y), line, font=font, fill=preset["title_color"])

    def _draw_keyword_pill(self, draw, keyword, preset):
        tag = f"#{keyword.replace(' ', '').lower()[:25]}"
        font = self._get_font(22)
        x, y, px, py = 28, THUMB_H - 62, 14, 8
        bbox = draw.textbbox((0, 0), tag, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle(
            [(x, y), (x + w + px * 2, y + h + py * 2)],
            radius=6, fill=(30, 30, 30), outline=preset["accent"], width=2,
        )
        draw.text((x + px, y + py), tag, font=font, fill=preset["accent"])

    def _draw_bottom_strip(self, img, preset):
        draw = ImageDraw.Draw(img)
        accent = preset["accent"]
        for x in range(THUMB_W):
            r = int(accent[0] * x / THUMB_W)
            g = int(accent[1] * x / THUMB_W)
            b = int(accent[2] * x / THUMB_W)
            draw.line([(x, THUMB_H - 6), (x, THUMB_H)], fill=(r, g, b))

    def _get_font(self, size, bold=False):
        candidates = (
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
            if bold else
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
        )
        for p in candidates:
            try:
                return ImageFont.truetype(p, size)
            except (IOError, OSError):
                continue
        return ImageFont.load_default()
