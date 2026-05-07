import json
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from reddit_automation.dashboard.server import DashboardServer
from reddit_automation.utils import paths as paths_module


class FakeCronService:
    def get_status(self):
        return {"enabled": False, "message": "mock"}

    def toggle(self):
        return {"enabled": False}

    def run_now(self):
        return {"status": "mock"}

    def stop(self):
        pass


def _minimal_config():
    return {
        "project": {
            "episode_target_minutes": 5,
            "final_pick_count": 3,
            "backup_pick_count": 2,
        },
        "sources": {"subreddits": ["AskReddit"]},
        "scoring": {
            "weights": {
                "reaction_potential": 0.40,
                "laugh_factor": 0.25,
                "story_payoff": 0.15,
                "clarity_after_rewrite": 0.10,
                "comment_bonus": 0.10,
            },
            "thresholds": {
                "min_reaction_potential": 8,
                "min_laugh_factor": 7,
                "min_overall_score": 7.2,
            },
        },
        "hosts": {
            "host_1": {"key": "host_1", "voice_id": "en-US-GuyNeural"},
            "host_2": {"key": "host_2", "voice_id": "en-US-AnaNeural"},
        },
        "render": {"resolution": "1920x1080"},
    }


def _write_config(config_dir: Path, payload: dict):
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _start_server():
    server = DashboardServer(db=None, pipeline_module=None, cron_service=FakeCronService(), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
    thread.start()
    time.sleep(0.2)
    return server, thread


def _get(url: str):
    with urlopen(url) as response:
        return response.status, json.loads(response.read().decode())


def _post(url: str, body: dict):
    request = Request(url, method="POST", data=json.dumps(body).encode("utf-8"))
    request.add_header("Content-Type", "application/json")
    with urlopen(request) as response:
        return response.status, json.loads(response.read().decode())


def test_config_endpoint_returns_full_editable_surface(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    _write_config(config_dir, _minimal_config())
    monkeypatch.setattr(paths_module, "CONFIG_DIR", config_dir)

    server, _ = _start_server()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        status, data = _get(f"{base}/api/config")
        assert status == 200
        assert data["project"]["render_dir"].endswith("/output/rendered")
        assert data["project"]["assets_dir"].endswith("/output/assets")
        assert data["project"]["episode_date"]
        assert data["output_dir"].endswith("/output")
        assert data["publishing"]["upload_tags"] == ["reddit", "reddit stories"]
        assert data["alerts"]["telegram_bot_token"] == ""
        assert data["alerts"]["telegram_chat_id"] == ""
        assert data["youtube"]["credentials_file"].endswith("/data/youtube_credentials.json")
        assert data["youtube"]["token_file"].endswith("/data/youtube_credentials.token")
        assert data["fal"]["model"] == "fal-ai/flux/schnell"
        assert data["reddit_test_data"] == {"submissions": []}
        assert data["cron"] == "24h"
    finally:
        server.shutdown()


def test_config_update_rejects_invalid_config_and_preserves_file(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    original = _minimal_config()
    _write_config(config_dir, original)
    monkeypatch.setattr(paths_module, "CONFIG_DIR", config_dir)

    server, _ = _start_server()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        status, result = _post(f"{base}/api/config/update", {"sources": {"subreddits": []}})
        assert status == 200
        assert "error" in result

        persisted = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
        assert persisted == original
    finally:
        server.shutdown()


def test_config_update_persists_optional_fields_and_lists(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    _write_config(config_dir, _minimal_config())
    monkeypatch.setattr(paths_module, "CONFIG_DIR", config_dir)

    server, _ = _start_server()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        _, editable = _get(f"{base}/api/config")
        editable["project"]["render_dir"] = "/tmp/rendered"
        editable["project"]["assets_dir"] = "/tmp/assets"
        editable["project"]["episode_date"] = "2026-04-15"
        editable["sources"]["subreddits"] = ["AskReddit", "tifu"]
        editable["publishing"]["upload_tags"] = ["funny", "reddit"]
        editable["alerts"]["telegram_bot_token"] = "token-123"
        editable["alerts"]["telegram_chat_id"] = "chat-456"
        editable["youtube"]["credentials_file"] = "/tmp/youtube.json"
        editable["youtube"]["token_file"] = "/tmp/youtube.token"
        editable["output_dir"] = "/tmp/output"
        editable["fal"]["model"] = "fal-ai/flux/dev"
        editable["cron"] = "12h"

        status, result = _post(f"{base}/api/config/update", editable)
        assert status == 200
        assert result == {"status": "updated"}

        persisted = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
        assert persisted["project"]["render_dir"] == "/tmp/rendered"
        assert persisted["project"]["assets_dir"] == "/tmp/assets"
        assert persisted["project"]["episode_date"] == "2026-04-15"
        assert persisted["sources"]["subreddits"] == ["AskReddit", "tifu"]
        assert persisted["publishing"]["upload_tags"] == ["funny", "reddit"]
        assert persisted["alerts"]["telegram_bot_token"] == "token-123"
        assert persisted["alerts"]["telegram_chat_id"] == "chat-456"
        assert persisted["youtube"]["credentials_file"] == "/tmp/youtube.json"
        assert persisted["youtube"]["token_file"] == "/tmp/youtube.token"
        assert persisted["output_dir"] == "/tmp/output"
        assert persisted["fal"]["model"] == "fal-ai/flux/dev"
        assert persisted["cron"] == "12h"
    finally:
        server.shutdown()


def test_index_html_uses_root_api_path():
    template_path = Path(__file__).resolve().parents[1] / "src/reddit_automation/dashboard/template.html"
    html = template_path.read_text(encoding="utf-8")
    assert "const API = '/api';" in html
