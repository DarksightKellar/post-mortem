"""Unit tests for YouTube Data API v3 client."""

import os
import unittest
from unittest.mock import MagicMock, patch

from reddit_automation.clients.youtube_client import YouTubeClient


class TestYouTubeClientInit(unittest.TestCase):

    def test_reads_api_key_from_config(self):
        config = {"youtube": {"api_key": "AIza-test"}}
        client = YouTubeClient(config)
        self.assertEqual(client.api_key, "AIza-test")

    def test_reads_api_key_from_env_fallback(self):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "env-key"}):
            config = {"youtube": {}}
            client = YouTubeClient(config)
        self.assertEqual(client.api_key, "env-key")

    def test_raises_when_no_creds_file(self):
        """When credentials file doesn't exist, _get_service raises."""
        config = {"youtube": {"credentials_file": "/nonexistent/creds.json"}}
        with patch.dict(os.environ, {}, clear=True):
            client = YouTubeClient(config)
        with self.assertRaises(FileNotFoundError):
            client._get_service()

    def test_reads_credentials_file_from_config(self):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "k"}):
            config = {"youtube": {"credentials_file": "/path/to/creds.json"}}
            client = YouTubeClient(config)
        self.assertEqual(client.credentials_file, "/path/to/creds.json")

    def test_default_privacy_is_private(self):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "k"}):
            client = YouTubeClient({"youtube": {}})
        self.assertEqual(client.privacy_status, "private")


class TestYouTubeClientUpload(unittest.TestCase):

    def _make_client(self):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-key"}):
            return YouTubeClient({"youtube": {}})

    @patch("reddit_automation.clients.youtube_client.YouTubeClient._get_service")
    def test_upload_returns_video_id_and_url(self, mock_service):
        mock_service.return_value.videos().insert().execute.return_value = {
            "id": "dQw4w9WgXcQ",
            "status": {"uploadStatus": "processed"},
        }

        client = self._make_client()
        with patch("builtins.open", unittest.mock.mock_open(read_data=b"fake video")):
            result = client.upload("/tmp/video.mp4", {"title": "Test Episode"})

        assert result["video_id"] == "dQw4w9WgXcQ"
        assert result["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result["status"] == "processed"

    @patch("reddit_automation.clients.youtube_client.YouTubeClient._get_service")
    def test_upload_includes_title_and_description(self, mock_service):
        captured_body = {}

        def capture_insert(**kwargs):
            captured_body["body"] = kwargs.get("body", {})
            mock_resp = MagicMock()
            mock_resp.execute.return_value = {"id": "v1"}
            return mock_resp

        mock_service.return_value.videos().insert = capture_insert

        client = self._make_client()
        with patch("builtins.open", unittest.mock.mock_open(read_data=b"v")):
            client.upload("/tmp/video.mp4", {
                "title": "My Title",
                "description": "My description here",
            })

        assert captured_body["body"]["snippet"]["title"] == "My Title"
        assert "My description here" in captured_body["body"]["snippet"]["description"]

    @patch("reddit_automation.clients.youtube_client.YouTubeClient._get_service")
    def test_upload_uses_privacy_from_config(self, mock_service):
        captured_body = {}

        def capture_insert(**kwargs):
            captured_body["body"] = kwargs.get("body", {})
            mock_resp = MagicMock()
            mock_resp.execute.return_value = {"id": "v1"}
            return mock_resp

        mock_service.return_value.videos().insert = capture_insert

        config = {
            "youtube": {},
            "publishing": {"default_privacy_status": "public"},
        }
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "k"}):
            client = YouTubeClient(config)

        with patch("builtins.open", unittest.mock.mock_open(read_data=b"v")):
            client.upload("/tmp/video.mp4", {"title": "T"})

        assert captured_body["body"]["status"]["privacyStatus"] == "public"

    @patch("reddit_automation.clients.youtube_client.YouTubeClient._get_service")
    def test_upload_includes_tags_from_config(self, mock_service):
        captured_body = {}

        def capture_insert(**kwargs):
            captured_body["body"] = kwargs.get("body", {})
            mock_resp = MagicMock()
            mock_resp.execute.return_value = {"id": "v1"}
            return mock_resp

        mock_service.return_value.videos().insert = capture_insert

        config = {
            "youtube": {},
            "publishing": {"upload_tags": ["reddit", "funny", "storytime"]},
        }
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "k"}):
            client = YouTubeClient(config)

        with patch("builtins.open", unittest.mock.mock_open(read_data=b"v")):
            client.upload("/tmp/video.mp4", {"title": "T"})

        assert captured_body["body"]["snippet"]["tags"] == ["reddit", "funny", "storytime"]

    @patch("reddit_automation.clients.youtube_client.YouTubeClient._get_service")
    def test_upload_raises_on_api_error(self, mock_service):
        from googleapiclient.errors import HttpError

        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_service.return_value.videos().insert.side_effect = HttpError(
            mock_resp, b'{"error":{"message":"bad request"}}'
        )

        client = self._make_client()
        with patch("builtins.open", unittest.mock.mock_open(read_data=b"v")):
            with self.assertRaises(HttpError):
                client.upload("/tmp/video.mp4", {"title": "T"})


class TestYouTubeClientAuth(unittest.TestCase):

    def test_get_service_raises_when_no_creds_file(self):
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "k"}):
            client = YouTubeClient({"youtube": {
                "credentials_file": "/nonexistent/creds.json",
                "token_file": "/nonexistent/token.json",
            }})

        with self.assertRaises(FileNotFoundError) as ctx:
            client._get_service()
        self.assertIn("credentials", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
