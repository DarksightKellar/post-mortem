"""YouTube Data API v3 client for video uploads using OAuth 2.0."""

import os
from typing import Optional

from reddit_automation.utils.paths import DATA_DIR


class YouTubeClient:
    """Upload videos to YouTube via the Data API v3.
    
    Requires:
      - google-api-python-client
      - google-auth-oauthlib
      - OAuth2 credentials file from Google Cloud Console
      
    First run opens a browser for consent. Subsequent runs use a cached
    refresh token — no browser needed for automated pipeline runs.
    """

    DEFAULT_CREDENTIALS_FILE = str(DATA_DIR / "youtube_credentials.json")

    def __init__(self, config: dict):
        self.config = config
        yt = config.get("youtube", {})
        pub = config.get("publishing", {})

        self.credentials_file = yt.get("credentials_file", self.DEFAULT_CREDENTIALS_FILE)
        self.token_file = yt.get("token_file")  # auto-derived from credentials_file
        self.privacy_status = pub.get("default_privacy_status", "private")
        self.tags = pub.get("upload_tags", ["reddit", "reddit stories", "commentary"])
        self.category_id = yt.get("category_id", "22")  # 22 = People & Blogs
        self.api_key = yt.get("api_key") or os.environ.get("YOUTUBE_API_KEY")

    def _get_service(self):
        """Build and return an authenticated youtube/v3 service."""
        import pickle
        from pathlib import Path

        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        creds_file = Path(self.credentials_file)
        if not creds_file.exists():
            raise FileNotFoundError(
                f"YouTube OAuth2 credentials not found at {self.credentials_file}. "
                "Download from Google Cloud Console → Credentials → OAuth 2.0 Client IDs."
            )

        # Derive token path next to credentials file
        token_path = self.token_file or str(creds_file.with_suffix(".token"))

        creds = None
        if Path(token_path).exists():
            with open(token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_file),
                    ["https://www.googleapis.com/auth/youtube.upload"],
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "wb") as f:
                pickle.dump(creds, f)

        return build("youtube", "v3", credentials=creds)

    def upload(self, video_path: str, metadata: dict) -> dict:
        """Upload a video to YouTube. Returns dict with video_id, url, status."""
        from googleapiclient.http import MediaFileUpload

        youtube = self._get_service()

        title = metadata.get("title", "Untitled")
        description = metadata.get("description", "")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": self.tags,
                "categoryId": self.category_id,
            },
            "status": {
                "privacyStatus": self.privacy_status,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/*",
            resumable=True,
            chunksize=-1,  # auto chunk size
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = request.execute()

        video_id = response.get("id")
        return {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "status": response.get("status", {}).get("uploadStatus", "unknown"),
            "privacy_status": self.privacy_status,
        }


def _check_requirements() -> bool:
    """Check if YouTube client dependencies are available."""
    try:
        import googleapiclient.discovery  # noqa
        import google_auth_oauthlib.flow  # noqa
        return True
    except ImportError:
        return False
