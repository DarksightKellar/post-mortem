"""Tests for the dashboard _trigger_run result interpretation."""

import json
import time
from threading import Thread
from unittest.mock import MagicMock
from urllib.request import urlopen, Request

from reddit_automation.dashboard.server import DashboardServer


class FakeCronService:
    def get_status(self):
        return {"enabled": False, "message": "mock"}
    def toggle(self):
        return {"enabled": False}
    def run_now(self):
        return {"status": "mock"}
    def stop(self):
        pass


class FakeDB:
    def __init__(self):
        self.db_path = ":memory:"


def _make_pipeline(result):
    """Return a fake pipeline module whose run_daily_pipeline returns *result*."""
    class Pipe:
        @staticmethod
        def run_daily_pipeline(progress_callback=None):
            if progress_callback:
                for stage in ["fetch", "filter", "store", "score", "select",
                              "outline", "script", "voice", "visuals", "render", "publish"]:
                    progress_callback("running", stage, f"Running: {stage}")
                    progress_callback("completed", stage, f"Completed: {stage}")
            return result
    return Pipe


def _start_server(pipeline_result):
    srv = DashboardServer(
        db=FakeDB(),
        pipeline_module=_make_pipeline(pipeline_result),
        cron_service=FakeCronService(),
        host="127.0.0.1",
        port=0,
    )
    t = Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
    t.start()
    time.sleep(0.3)
    return srv, t


def _get(url):
    with urlopen(url) as r:
        return r.status, json.loads(r.read().decode())


def _post(url):
    req = Request(url, method="POST", data=b"")
    with urlopen(req) as r:
        return r.status, json.loads(r.read().decode())


class TestTriggerRunResultInterpretation:
    """Verify the dashboard reports the correct outcome for each pipeline result type."""

    def test_no_episode_shows_completed_not_success(self, tmp_path):
        """When pipeline returns no_episode, dashboard must NOT say 'success' or 'completed successfully'."""
        pipeline_result = {
            "status": "no_episode",
            "reason": "no_selected_items",
        }
        srv, t = _start_server(pipeline_result)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")

        # Wait for the pipeline to finish
        for _ in range(20):
            _, state = _get(f"{base}/api/run/status")
            if state.get("status") in ("completed", "failed"):
                break
            time.sleep(0.5)

        assert state["status"] == "completed", f"Expected completed, got {state['status']}"
        assert "no episode" in state["message"].lower(), (
            f"Message should mention 'no episode', got: {state['message']}"
        )
        # Must NOT say "successful" or imply success
        assert "successful" not in state["message"].lower(), (
            f"no_episode result must NOT say 'successful': {state['message']}"
        )

        srv.shutdown()

    def test_empty_result_shows_failed(self):
        """When pipeline returns an empty dict, dashboard must mark it failed."""
        srv, t = _start_server({})
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")

        for _ in range(20):
            _, state = _get(f"{base}/api/run/status")
            if state.get("status") in ("completed", "failed"):
                break
            time.sleep(0.5)

        assert state["status"] == "failed", f"Expected failed for empty result, got {state}"

        srv.shutdown()

    def test_success_with_title_shows_completed_with_title(self):
        """When pipeline returns a real success, dashboard shows Completed: <title>."""
        srv, t = _start_server({
            "status": "success",
            "run_date": "2026-04-05",
            "title": "Test Episode Title",
        })
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")

        for _ in range(20):
            _, state = _get(f"{base}/api/run/status")
            if state.get("status") in ("completed", "failed"):
                break
            time.sleep(0.5)

        assert state["status"] == "completed"
        assert "Test Episode Title" in state["message"], (
            f"Expected title in message, got: {state['message']}"
        )

        srv.shutdown()

    def test_exception_shows_failed(self):
        """When pipeline raises, dashboard must show failed with error."""
        class BrokenPipeline:
            @staticmethod
            def run_daily_pipeline(progress_callback=None):
                raise ConnectionError("network unreachable")

        srv = DashboardServer(
            db=FakeDB(),
            pipeline_module=BrokenPipeline(),
            cron_service=FakeCronService(),
            host="127.0.0.1",
            port=0,
        )
        t = Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
        t.start()
        time.sleep(0.3)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")

        for _ in range(20):
            _, state = _get(f"{base}/api/run/status")
            if state.get("status") in ("completed", "failed"):
                break
            time.sleep(0.5)

        assert state["status"] == "failed"
        assert "network unreachable" in state["message"]

        srv.shutdown()
