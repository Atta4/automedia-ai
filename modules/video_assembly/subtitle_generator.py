from pathlib import Path
from dataclasses import dataclass
from loguru import logger


@dataclass
class SubtitleEntry:
    index: int
    start_sec: float
    end_sec: float
    text: str


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = int(seconds // 60) % 60
    h = int(seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _split_into_lines(text: str, max_chars: int = 42) -> list[str]:
    """
    Split text into subtitle lines of max_chars each.
    Tries to break at word boundaries.
    """
    words = text.split()
    lines = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    # Max 2 lines per subtitle card
    return lines[:2]


def generate_srt(
    segments: list[dict],
    segment_durations: list[float],
    output_path: Path,
    words_per_card: int = 8,
) -> Path:
    """
    Generate an SRT subtitle file from script segments and their audio durations.

    segments: list of {"label": str, "text": str, "order": int}
    segment_durations: real audio duration in seconds per segment (same order)
    words_per_card: how many words per subtitle card (smaller = more dynamic)
    """
    entries: list[SubtitleEntry] = []
    current_time = 0.0
    card_index = 1

    for seg, duration in zip(segments, segment_durations):
        text = seg.get("text", "").strip()
        if not text or duration <= 0:
            current_time += duration
            continue

        words = text.split()
        total_words = len(words)
        if total_words == 0:
            current_time += duration
            continue

        # Split segment into multiple subtitle cards
        sec_per_word = duration / total_words
        i = 0
        seg_start = current_time

        while i < total_words:
            card_words = words[i: i + words_per_card]
            card_text = " ".join(card_words)
            card_duration = len(card_words) * sec_per_word

            start = seg_start + (i * sec_per_word)
            end = min(start + card_duration, seg_start + duration - 0.05)

            lines = _split_into_lines(card_text)
            display_text = "\n".join(lines)

            entries.append(SubtitleEntry(
                index=card_index,
                start_sec=start,
                end_sec=end,
                text=display_text,
            ))
            card_index += 1
            i += words_per_card

        current_time += duration

    # Write SRT file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(f"{entry.index}\n")
            f.write(f"{_format_timestamp(entry.start_sec)} --> {_format_timestamp(entry.end_sec)}\n")
            f.write(f"{entry.text}\n\n")

    logger.success(f"SRT generated: {output_path.name} | {len(entries)} cards")
    return output_path


def generate_ass_subtitles(
    segments: list[dict],
    segment_durations: list[float],
    output_path: Path,
    style: str = "modern",
) -> Path:
    """
    Generate ASS subtitle file with modern social-media styling.
    ASS format supports color, font size, outline, shadow — much better than SRT.

    Styles:
      modern  → white bold text, black outline, bottom-center (YouTube style)
      caption → yellow text, lower-third box (news caption style)
    """
    styles = {
        "modern": (
            "Style: Default,Arial,22,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            "1,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1"
        ),
        "caption": (
            "Style: Default,Arial Bold,20,&H0000FFFF,&H000000FF,&H00000000,&H80000000,"
            "1,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1"
        ),
    }
    chosen_style = styles.get(style, styles["modern"])

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{chosen_style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def _ass_time(sec: float) -> str:
        cs = int((sec % 1) * 100)
        s = int(sec) % 60
        m = int(sec // 60) % 60
        h = int(sec // 3600)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    events = []
    current_time = 0.0
    words_per_card = 8

    for seg, duration in zip(segments, segment_durations):
        text = seg.get("text", "").strip()
        if not text or duration <= 0:
            current_time += duration
            continue

        words = text.split()
        total_words = len(words)
        if total_words == 0:
            current_time += duration
            continue

        sec_per_word = duration / total_words
        i = 0
        seg_start = current_time

        while i < total_words:
            card_words = words[i: i + words_per_card]
            card_text = " ".join(card_words)
            start = seg_start + (i * sec_per_word)
            end = min(start + len(card_words) * sec_per_word, seg_start + duration - 0.05)

            events.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},"
                f"Default,,0,0,0,,{card_text}"
            )
            i += words_per_card

        current_time += duration

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))

    logger.success(f"ASS subtitles generated: {output_path.name} | {len(events)} cards")
    return output_path
