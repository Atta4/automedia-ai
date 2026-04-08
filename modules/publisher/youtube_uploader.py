import asyncio
import os
from pathlib import Path
from loguru import logger

from config.settings import get_settings


class YouTubeUploader:
    """
    Uploads approved videos to YouTube via YouTube Data API v3.

    Setup required:
      1. Google Cloud Console → create OAuth2 credentials
      2. Download client_secrets.json → place in project root
      3. First run: browser OAuth flow (token saved to youtube_token.json)
      4. Subsequent runs: uses saved token automatically

    Scopes needed:
      https://www.googleapis.com/auth/youtube.upload
      https://www.googleapis.com/auth/youtube
    """

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]
    TOKEN_FILE = "youtube_token.json"
    SECRETS_FILE = "client_secrets.json"

    def __init__(self):
        self.settings = get_settings()
        self._service = None

    # ── Public API ────────────────────────────────────────────────────────────

    async def upload(
        self,
        video_path: Path,
        title: str,
        description: str,
        hashtags: list[str],
        thumbnail_path: Path | None = None,
        category_id: str = "25",     # 25 = News & Politics
        privacy: str = "private",    # Start private → review → make public manually
    ) -> dict:
        """
        Upload a video to YouTube.
        Returns dict with video_id, url, and status.

        privacy: private | unlisted | public
        category_id:
          1=Film, 2=Autos, 10=Music, 17=Sports, 22=People,
          24=Entertainment, 25=News, 26=HowTo, 28=Science
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._upload_sync,
            video_path, title, description, hashtags,
            thumbnail_path, category_id, privacy,
        )
        return result

    # ── Sync upload (runs in thread pool) ────────────────────────────────────

    def _upload_sync(
        self,
        video_path: Path,
        title: str,
        description: str,
        hashtags: list[str],
        thumbnail_path: Path | None,
        category_id: str,
        privacy: str,
    ) -> dict:
        try:
            from googleapiclient.http import MediaFileUpload
            service = self._get_service()
        except ImportError:
            logger.error("google-api-python-client not installed for upload")
            return {"status": "error", "message": "Missing google-api-python-client"}
        except Exception as e:
            logger.error(f"YouTube auth failed: {e}")
            return {"status": "error", "message": str(e)}

        # Build tags list (YouTube tags = hashtags without #)
        tags = [t.lstrip("#") for t in hashtags][:30]  # YouTube max 30 tags

        # Append hashtags to description for discoverability
        hashtag_str = " ".join(f"#{t}" for t in tags[:10])
        full_description = f"{description}\n\n{hashtag_str}"

        body = {
            "snippet": {
                "title": title[:100],
                "description": full_description[:5000],
                "tags": tags,
                "categoryId": category_id,
                "defaultLanguage": self.settings.content_language,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,   # 10MB chunks
        )

        logger.info(f"Uploading to YouTube: '{title}' ({video_path.stat().st_size / 1e6:.1f}MB)")

        request = service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")

        video_id = response.get("id", "")
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Set thumbnail if provided
        if thumbnail_path and thumbnail_path.exists() and video_id:
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
                ).execute()
                logger.success(f"Thumbnail uploaded for {video_id}")
            except Exception as e:
                logger.warning(f"Thumbnail upload failed: {e}")

        logger.success(f"YouTube upload complete: {url}")
        return {
            "status": "success",
            "video_id": video_id,
            "url": url,
            "privacy": privacy,
            "title": title,
        }

    def _get_service(self):
        """Build authenticated YouTube API service (OAuth2)."""
        if self._service:
            return self._service

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None

        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.SECRETS_FILE):
                    raise FileNotFoundError(
                        f"Missing {self.SECRETS_FILE}. "
                        "Download from Google Cloud Console → APIs → Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.SECRETS_FILE, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        self._service = build("youtube", "v3", credentials=creds)
        return self._service
