import json
import urllib.request
from unittest.mock import MagicMock
from reddit_automation.pipeline import notify as notify_module


def test_send_run_notification_delivers_success_when_enabled(monkeypatch):
    config = {"alerts": {"telegram_on_success": True, "telegram_on_failure": False}}
    deliveries = []

    def fake_deliver(message, received_config):
        deliveries.append((message, received_config))

    monkeypatch.setattr(notify_module, "_deliver_notification", fake_deliver, raising=False)

    notify_module.send_run_notification("success", "Episode published successfully: Test Title", config)

    assert deliveries == [("Episode published successfully: Test Title", config)]


def test_send_run_notification_skips_success_when_disabled(monkeypatch):
    config = {"alerts": {"telegram_on_success": False, "telegram_on_failure": True}}
    deliveries = []

    def fake_deliver(message, received_config):
        deliveries.append((message, received_config))

    monkeypatch.setattr(notify_module, "_deliver_notification", fake_deliver, raising=False)

    notify_module.send_run_notification("success", "Episode published successfully: Test Title", config)

    assert deliveries == []


def test_send_run_notification_delivers_failure_when_enabled(monkeypatch):
    config = {"alerts": {"telegram_on_success": False, "telegram_on_failure": True}}
    deliveries = []

    def fake_deliver(message, received_config):
        deliveries.append((message, received_config))

    monkeypatch.setattr(notify_module, "_deliver_notification", fake_deliver, raising=False)

    notify_module.send_run_notification("failure", "upload failed", config)

    assert deliveries == [("upload failed", config)]


def test_send_run_notification_skips_failure_when_disabled(monkeypatch):
    config = {"alerts": {"telegram_on_success": True, "telegram_on_failure": False}}
    deliveries = []

    def fake_deliver(message, received_config):
        deliveries.append((message, received_config))

    monkeypatch.setattr(notify_module, "_deliver_notification", fake_deliver, raising=False)

    notify_module.send_run_notification("failure", "upload failed", config)

    assert deliveries == []


def test_deliver_notification_uses_telegram_bot_api(monkeypatch):
    """_deliver_notification sends a POST to the Telegram Bot API with bot token and chat ID."""
    config = {
        "alerts": {
            "telegram_bot_token": "TEST_BOT_TOKEN",
            "telegram_chat_id": "123456789",
        }
    }

    captured = {}

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["data"] = request.data.decode() if request.data else ""
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    notify_module._deliver_notification("Episode 42 published", config)

    assert captured["url"].endswith("TEST_BOT_TOKEN/sendMessage")
    assert captured["method"] == "POST"
    body = json.loads(captured["data"])
    assert body["chat_id"] == "123456789"
    assert "Episode 42 published" in body["text"]


def test_deliver_notification_handles_missing_config_gracefully():
    """_deliver_notification with no telegram config should not crash."""
    config = {"alerts": {}}
    # Should not raise
    notify_module._deliver_notification("This message is sent", config)


def test_deliver_notification_raises_on_telegram_error(monkeypatch):
    """_deliver_notification raises when Telegram API returns an error response."""
    config = {
        "alerts": {
            "telegram_bot_token": "BAD_TOKEN",
            "telegram_chat_id": "123456789",
        }
    }

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self):
            return b'{"ok": false, "description": "Bad Request: chat not found"}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda req: FakeResponse())

    import pytest
    with pytest.raises(RuntimeError, match="Telegram API error"):
        notify_module._deliver_notification("Test", config)
