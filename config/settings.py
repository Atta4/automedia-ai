from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_llm_model: str = Field("gpt-4o", env="OPENAI_LLM_MODEL")

    # External APIs
    newsapi_key: str = Field("", env="NEWSAPI_KEY")
    youtube_api_key: str = Field("", env="YOUTUBE_API_KEY")
    pexels_api_key: str = Field("", env="PEXELS_API_KEY")
    pixabay_api_key: str = Field("", env="PIXABAY_API_KEY")
    elevenlabs_api_key: str = Field("", env="ELEVENLABS_API_KEY")

    # Social Media APIs
    twitter_bearer_token: str = Field("", env="TWITTER_BEARER_TOKEN")
    reddit_client_id: str = Field("", env="REDDIT_CLIENT_ID")
    reddit_client_secret: str = Field("", env="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field("AutoMediaAI/1.0", env="REDDIT_USER_AGENT")

    # Telegram (optional)
    telegram_api_id: str = Field("", env="TELEGRAM_API_ID")
    telegram_api_hash: str = Field("", env="TELEGRAM_API_HASH")
    telegram_channels: str = Field("", env="TELEGRAM_CHANNELS")

    # Facebook/Meta (NEW - for Facebook upload)
    facebook_page_id: str = Field("", env="FACEBOOK_PAGE_ID")
    facebook_page_access_token: str = Field("", env="FACEBOOK_PAGE_ACCESS_TOKEN")
    instagram_account_id: str = Field("", env="INSTAGRAM_ACCOUNT_ID")

    # RSS Feeds (pipe-separated list)
    custom_rss_feeds: str = Field("", env="CUSTOM_RSS_FEEDS")

    # Database
    mongodb_uri: str = Field("mongodb://localhost:27017", env="MONGODB_URI")
    mongodb_db: str = Field("automedia_ai", env="MONGODB_DB")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # App
    app_env: str = Field("development", env="APP_ENV")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    output_dir: str = Field("./output", env="OUTPUT_DIR")
    temp_dir: str = Field("./temp", env="TEMP_DIR")

    # ── Content General ───────────────────────────────────────────────────
    min_sources_to_validate: int = Field(3, env="MIN_SOURCES_TO_VALIDATE")
    max_topics_per_run: int = Field(10, env="MAX_TOPICS_PER_RUN")
    content_language: str = Field("en", env="CONTENT_LANGUAGE")
    trending_region: str = Field("US", env="TRENDING_REGION")

    # ── Video Format ──────────────────────────────────────────────────────
    # Format: shorts (9:16, 60s) | standard (16:9, 90s) | both
    video_format: str = Field("standard", env="VIDEO_FORMAT")

    # Resolution: 1080p | 720p | 4k
    video_resolution: str = Field("1080p", env="VIDEO_RESOLUTION")

    # Target duration (auto-set based on format)
    target_video_duration: int = Field(90, env="TARGET_VIDEO_DURATION")

    # ── TTS Voice ─────────────────────────────────────────────────────────
    # Provider: openai | elevenlabs
    tts_provider: str = Field("openai", env="TTS_PROVIDER")

    # OpenAI voice (or "auto" for content-based selection)
    openai_tts_voice: str = Field("auto", env="OPENAI_TTS_VOICE")

    # Volume boost (1.0 = normal, 1.5 = 50% louder, 2.0 = double)
    tts_volume_boost: float = Field(1.6, env="TTS_VOLUME_BOOST")

    # ── Content Focus ─────────────────────────────────────────────────────
    focus_keywords: str = Field(
        "Israel Gaza war,Israel Hamas,Netanyahu,IDF military,Israel politics,"
        "Pakistan politics,Pakistan army,Imran Khan,Pakistan economy,Pakistan news",
        env="FOCUS_KEYWORDS"
    )
    content_perspective: str = Field("balanced", env="CONTENT_PERSPECTIVE")
    blocked_topics: str = Field("", env="BLOCKED_TOPICS")
    content_niche: str = Field("current_affairs", env="CONTENT_NICHE")  # NEW: Multi-niche support

    # ── Script Language ───────────────────────────────────────────────────
    # Script output language: en | ur | ar | hi | auto
    script_language: str = Field("en", env="SCRIPT_LANGUAGE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_focus_keywords(self) -> list[str]:
        return [k.strip() for k in self.focus_keywords.split(",") if k.strip()]

    def get_blocked_topics(self) -> list[str]:
        return [k.strip().lower() for k in self.blocked_topics.split(",") if k.strip()]

    def get_video_dimensions(self) -> tuple[int, int]:
        """Returns (width, height) based on format + resolution."""
        res_map = {"1080p": (1920, 1080), "720p": (1280, 720), "4k": (3840, 2160)}
        w, h = res_map.get(self.video_resolution, (1280, 720))
        if self.video_format == "shorts":
            return h, w  # 9:16 portrait
        return w, h  # 16:9 landscape

    def get_duration(self) -> int:
        if self.video_format == "shorts":
            return min(self.target_video_duration, 58)  # YouTube Shorts max 60s
        return self.target_video_duration

    def get_telegram_channels(self) -> list[str]:
        """Parse Telegram channel list (comma-separated)."""
        return [ch.strip() for ch in self.telegram_channels.split(",") if ch.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()