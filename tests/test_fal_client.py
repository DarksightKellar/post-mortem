"""Unit tests for fal.ai image generation client."""

import os
import unittest
from unittest.mock import MagicMock, patch

from reddit_automation.utils.fal_client import FalClient


class TestFalClientInit(unittest.TestCase):
    def test_instantiates_with_api_key(self):
        with patch.dict(os.environ, {"FAL_KEY": "sk-test-123"}):
            client = FalClient()
        self.assertEqual(client.api_key, "sk-test-123")

    def test_raises_when_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                FalClient(api_key=None)
            self.assertIn("FAL_KEY", str(ctx.exception))

    def test_uses_model_from_config(self):
        config = {"fal": {"model": "fal-ai/flux/schnell"}}
        with patch.dict(os.environ, {"FAL_KEY": "sk-test"}):
            client = FalClient(api_key="sk-test", config=config)
        self.assertEqual(client.model, "fal-ai/flux/schnell")

    def test_default_model(self):
        with patch.dict(os.environ, {"FAL_KEY": "sk-test"}):
            client = FalClient()
        self.assertIn("flux", client.model)


class TestFalClientPollTimeout(unittest.TestCase):
    def _make_client(self):
        with patch.dict(os.environ, {"FAL_KEY": "sk-test"}):
            return FalClient()

    @patch("reddit_automation.utils.fal_client.time.sleep", return_value=None)
    @patch("reddit_automation.utils.fal_client.FalClient._get_result")
    @patch("reddit_automation.utils.fal_client.FalClient._check_status")
    @patch("reddit_automation.utils.fal_client.FalClient._submit")
    def test_generate_raises_on_poll_timeout(self, mock_submit, mock_status, mock_get_result, mock_sleep):
        mock_submit.return_value = "req-abc-123"
        # Always returns IN_PROGRESS — simulates a hung job
        mock_status.return_value = {"status": "IN_PROGRESS"}

        client = self._make_client()
        with self.assertRaises(RuntimeError) as ctx:
            client.generate("a cat", output_path="/tmp/timeout.png", max_retries=3)
        self.assertIn("timed out", str(ctx.exception))
        self.assertEqual(mock_status.call_count, 3)

    @patch("reddit_automation.utils.fal_client.FalClient.download_image", return_value="/tmp/img.png")
    @patch("reddit_automation.utils.fal_client.FalClient._get_result")
    @patch("reddit_automation.utils.fal_client.FalClient._check_status")
    @patch("reddit_automation.utils.fal_client.FalClient._submit")
    def test_generate_completes_after_multiple_polls(self, mock_submit, mock_status, mock_get_result, mock_download):
        mock_submit.return_value = "req-abc-123"
        mock_status.side_effect = [
            {"status": "IN_PROGRESS"},
            {"status": "IN_PROGRESS"},
            {"status": "COMPLETED"},
        ]
        mock_get_result.return_value = {
            "images": [{"url": "https://example.com/done.png"}]
        }

        client = self._make_client()
        result = client.generate("a cat", output_path="/tmp/done.png")

        self.assertEqual(result, "/tmp/done.png")
        self.assertEqual(mock_status.call_count, 3)
        mock_get_result.assert_called_once_with("req-abc-123")
        mock_download.assert_called_once_with("https://example.com/done.png", "/tmp/done.png")

    @patch("reddit_automation.utils.fal_client.FalClient._get_result")
    @patch("reddit_automation.utils.fal_client.FalClient._check_status")
    @patch("reddit_automation.utils.fal_client.FalClient._submit")
    def test_generate_raises_when_no_images_in_result(self, mock_submit, mock_status, mock_get_result):
        mock_submit.return_value = "req-abc-123"
        mock_status.return_value = {"status": "COMPLETED"}
        mock_get_result.return_value = {"images": []}

        client = self._make_client()
        with self.assertRaises(RuntimeError) as ctx:
            client.generate("a cat", output_path="/tmp/empty.png")
        self.assertIn("No images", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
