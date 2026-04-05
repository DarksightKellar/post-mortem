"""Unit tests for the dashboard server."""

import json
import unittest
from http.server import HTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from reddit_automation.dashboard.server import DashboardServer


class TestDashboardServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Start the server on a test port."""
        cls.port = 19876
        cls.runs_data = [
            {
                "run_date": "2026-04-03",
                "stage": "publish",
                "status": "success",
                "message": "Episode published successfully",
                "payload_json": '{"title": "Test episode"}',
            },
            {
                "run_date": "2026-04-02",
                "stage": "fetch",
                "status": "failure",
                "message": "Reddit API timeout",
                "payload_json": '{"error_type": "ConnectionError"}',
            },
        ]
        cls.config_data = {
            "project": {"episode_target_minutes": 5},
            "sources": {"subreddits": ["AskReddit"]},
            "publishing": {"default_privacy_status": "private"},
        }
        cls.cron_data = {"enabled": True, "next_run_at": "2026-04-04T09:00:00"}

        def fake_load(config):
            # Return a list of dicts (not raw DB rows)
            rows = []
            for r in cls.runs_data:
                row = dict(r)
                if isinstance(r.get("payload_json"), str):
                    row["payload"] = json.loads(r["payload_json"])
                rows.append(row)
            return rows

        def fake_update_config(updates):
            cls.config_data.update(updates)
            return cls.config_data

        def fake_cron_status():
            return cls.cron_data

        def fake_cron_toggle():
            cls.cron_data["enabled"] = not cls.cron_data["enabled"]
            return cls.cron_data

        def fake_cron_run():
            return {"status": "triggered"}

        class FakeDB:
            def load_run_logs(self, limit=50):
                return fake_load(cls.config_data)[:limit]

            def load_config(self):
                return cls.config_data

            def update_config(self, updates):
                return fake_update_config(updates)

        cls.db = FakeDB()

        class FakeCronService:
            def get_status(self):
                return cls.cron_data
            def toggle(self):
                return fake_cron_toggle()
            def run_now(self):
                return fake_cron_run()

        cls.server = DashboardServer(db=cls.db, cron_service=FakeCronService(), port=cls.port)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        with urlopen(f"http://127.0.0.1:{self.port}{path}") as resp:
            return resp.status, json.loads(resp.read().decode())

    def _post(self, path):
        req = Request(f"http://127.0.0.1:{self.port}{path}", method="POST", data=b"")
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())

    def test_index_returns_html(self):
        with urlopen(f"http://127.0.0.1:{self.port}/") as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode()
            self.assertIn("<!DOCTYPE html>", body)
            self.assertIn("Dashboard", body)

    def test_stats_endpoint(self):
        status, data = self._get("/api/stats")
        self.assertEqual(status, 200)
        self.assertIn("total_runs", data)
        self.assertIn("success_rate", data)
        self.assertIn("last_7_days", data)
        self.assertEqual(data["total_runs"], 2)
        self.assertEqual(data["success_rate"], 50.0)

    def test_runs_endpoint(self):
        status, data = self._get("/api/runs")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["stage"], "publish")

    def test_runs_limit(self):
        status, data = self._get("/api/runs?limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 1)

    def test_config_endpoint(self):
        status, data = self._get("/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(data["project"]["episode_target_minutes"], 5)

    def test_config_update_accepts_valid_keys(self):
        status, data = self._post("/api/config/update")
        self.assertEqual(status, 200)

    def test_config_update_rejects_unauthorized_keys(self):
        """Prove the whitelist rejects arbitrary keys that could inject new config sections."""
        import json
        payload = json.dumps({
            "__malicious_injected_section": {"evil": True},
            "project": {"episode_target_minutes": 99},
        }).encode()
        req = Request(f"http://127.0.0.1:{self.port}/api/config/update", data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        with urlopen(req) as resp:
            result = json.loads(resp.read().decode())

        # The update should have been applied, but the malicious key should NOT appear
        updated = self._get("/api/config")[1]
        assert "__malicious_injected_section" not in updated, \
            "SECURITY BUG: arbitrary config section was injected"

    def test_cron_status_endpoint(self):
        status, data = self._get("/api/cron")
        self.assertEqual(status, 200)
        self.assertIn("enabled", data)
        self.assertTrue(data["enabled"])

    def test_cron_toggle(self):
        # Toggle off
        status, data = self._post("/api/cron/toggle")
        self.assertEqual(status, 200)
        self.assertFalse(data["enabled"])

        # Toggle back on
        status, data = self._post("/api/cron/toggle")
        self.assertEqual(status, 200)
        self.assertTrue(data["enabled"])

    def test_cron_run(self):
        status, data = self._post("/api/cron/run")
        self.assertEqual(status, 200)
        self.assertIn("status", data)

    def test_unknown_path_returns_404(self):
        try:
            urlopen(f"http://127.0.0.1:{self.port}/nonexistent")
        except HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
