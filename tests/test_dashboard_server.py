"""Dashboard UI flow tests — every endpoint and interaction path."""

import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from reddit_automation.dashboard.server import DashboardServer


# ── Fakes ──

PIPELINE_STAGES = [
    "fetch", "filter", "store", "score", "select",
    "outline", "script", "voice", "visuals", "render", "publish",
]


class FakeCronService:
    def __init__(self, enabled=True):
        self._enabled = enabled

    def get_status(self):
        return {"enabled": self._enabled, "next_run_at": "2026-04-06T09:00:00"}

    def toggle(self):
        self._enabled = not self._enabled
        return {"enabled": self._enabled}

    def run_now(self):
        return {"status": "triggered"}

    def stop(self):
        pass


class _FakeCursor:
    """Mimics sqlite3 cursor. Extracts LIMIT from params for realistic test behavior."""
    def __init__(self, rows):
        self._rows = rows
        self._limit = None

    def execute(self, sql, params=None):
        # Extract LIMIT from SQL for realistic behavior
        if "LIMIT" in sql.upper() and params:
            try:
                self._limit = int(params[0])
            except (ValueError, IndexError):
                pass
        return self

    def fetchall(self):
        if self._limit is not None:
            return self._rows[:self._limit]
        return self._rows


class _FakeConn:
    """Context manager wrapping a fake sqlite3 connection."""
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return _FakeCursor(self._rows)

    def __exit__(self, *args):
        pass


class FakeDB:
    """Matches both RunLogRepository and Database APIs."""
    def __init__(self, runs=None):
        self.runs = runs or []
        self.db_path = ":memory:"

    def get_recent(self, limit=50):
        return self.runs[:limit]

    def connect(self):
        return _FakeConn(self.runs)


# ── Helpers ──

def _make_pipeline(result):
    """Return a fake pipeline module whose run_daily_pipeline returns *result*."""
    class Pipe:
        @staticmethod
        def run_daily_pipeline(progress_callback=None):
            if progress_callback:
                for stage in PIPELINE_STAGES:
                    progress_callback("running", stage, f"Running: {stage}")
                    progress_callback("completed", stage, f"Completed: {stage}")
            return result
    return Pipe


def _make_slow_pipeline(result, delay=0.5):
    """Pipeline that takes *delay* seconds so polling tests can catch running state."""
    class SlowPipe:
        @staticmethod
        def run_daily_pipeline(progress_callback=None):
            if progress_callback:
                progress_callback("running", "fetch", "Running: fetch")
            time.sleep(delay)
            if progress_callback:
                progress_callback("completed", "fetch", "Completed: fetch")
            return result
    return SlowPipe


def _make_broken_pipeline(exc):
    class BrokenPipe:
        @staticmethod
        def run_daily_pipeline(progress_callback=None):
            raise exc
    return BrokenPipe


def _start(cfg, **kv):
    srv = DashboardServer(db=cfg.get("db"), pipeline_module=cfg.get("pm"),
                           cron_service=cfg.get("cron"), **kv)
    t = threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True)
    t.start()
    time.sleep(0.2)
    return srv, t


def _get_raw(url):
    """GET, returns (status_code, raw_bytes)."""
    with urlopen(url) as r:
        return r.status, r.read()


def _get(url):
    """GET, returns (status_code, parsed_json). Assumes JSON response."""
    with urlopen(url) as r:
        return r.status, json.loads(r.read().decode())


def _post_raw(path, body=None):
    data = json.dumps(body).encode() if body else b""
    req = Request(path, method="POST", data=data)
    if body:
        req.add_header("Content-Type", "application/json")
    with urlopen(req) as r:
        return r.status, r.read()


def _post(path, body=None):
    data = json.dumps(body).encode() if body else b""
    req = Request(path, method="POST", data=data)
    if body:
        req.add_header("Content-Type", "application/json")
    with urlopen(req) as r:
        return r.status, json.loads(r.read().decode())


SAMPLE_RUNS = [
    {"run_date": "2026-04-03", "stage": "publish", "status": "success",
     "message": "Episode published", "payload_json": '{"title": "Test episode"}'},
    {"run_date": "2026-04-02", "stage": "fetch", "status": "failure",
     "message": "Reddit API timeout", "payload_json": '{"error_type": "ConnectionError"}'},
]


# ── Test class ──

class TestDashboardServer:

    @classmethod
    def setup_class(cls):
        fake_runs = FakeDB(runs=SAMPLE_RUNS)
        fake_cron = FakeCronService(enabled=True)
        fake_pm = _make_pipeline(
            {"status": "success", "title": "Test episode"}
        )
        cls.srv, cls.t = _start(
            {"db": fake_runs, "cron": fake_cron, "pm": fake_pm},
            host="127.0.0.1", port=0,
        )
        cls.port = cls.srv.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def teardown_class(cls):
        cls.srv.shutdown()

    # -- 1. HTML renders -----------------------------------------------------

    def test_index_returns_html_with_dashboard_title(self):
        s, body = _get_raw(f"{self.base}/")
        assert s == 200
        text = body.decode()
        assert "<!DOCTYPE html>" in text
        assert "Dashboard" in text
        assert "config-editor" in text
        assert "run-now-btn" in text
        assert "cron-toggle" in text

    # -- 2. Stats endpoint ---------------------------------------------------

    def test_stats_returns_totals_and_rate(self):
        s, d = _get(f"{self.base}/api/stats")
        assert s == 200
        assert d["total_runs"] == 2
        assert d["success_rate"] == 50.0
        assert "last_7_days" in d

    # -- 3. Runs endpoint ----------------------------------------------------

    def test_runs_returns_recent_entries(self):
        s, d = _get(f"{self.base}/api/runs")
        assert s == 200
        assert isinstance(d, list)
        assert len(d) == 2
        assert d[0]["stage"] == "publish"

    def test_runs_with_limit(self):
        s, d = _get(f"{self.base}/api/runs?limit=1")
        assert s == 200
        assert len(d) == 1

    def test_runs_empty_list_returns_empty_array(self):
        """Even with an empty DB, runs returns []."""
        empty_db = FakeDB(runs=[])
        srv = DashboardServer(db=empty_db, cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"
        s, d = _get(f"{base}/api/runs")
        assert s == 200
        assert d == []
        srv.shutdown()

    # -- 4. Config endpoint --------------------------------------------------

    def test_config_returns_yaml(self):
        s, d = _get(f"{self.base}/api/config")
        assert s == 200
        assert "project" in d
        assert d["project"]["episode_target_minutes"] == 5

    # -- 5. Cron endpoints ---------------------------------------------------

    def test_cron_status_reports_enabled(self):
        s, d = _get(f"{self.base}/api/cron")
        assert s == 200
        assert d["enabled"] is True

    def test_cron_toggle_flips_state(self):
        # toggle off
        s, d = _post(f"{self.base}/api/cron/toggle")
        assert s == 200
        assert d["enabled"] is False
        # toggle back
        s, d = _post(f"{self.base}/api/cron/toggle")
        assert s == 200
        assert d["enabled"] is True

    def test_cron_run_triggers(self):
        s, d = _post(f"{self.base}/api/cron/run")
        assert s == 200
        assert "status" in d

    # -- 6. Run Now → progress -----------------------------------------------

    def test_run_now_returns_started(self):
        s, d = _post(f"{self.base}/api/cron/run")
        assert s == 200
        assert d["status"] == "started"

    def test_concurrent_run_now_blocked(self):
        """Second Run Now while pipeline is running returns error."""
        pm = _make_slow_pipeline(
            {"status": "success", "title": "Slow episode"},
            delay=1.0,
        )
        db = FakeDB(runs=[])
        srv = DashboardServer(db=db, pipeline_module=pm,
                              cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")   # first
        time.sleep(0.3)                  # state is running
        s, d = _post(f"{base}/api/cron/run")   # second
        assert s == 200
        assert "error" in d
        srv.shutdown()

    def test_run_status_polling_reports_running(self):
        """While pipeline runs, /api/run/status returns running + stages."""
        pm = _make_slow_pipeline(
            {"status": "success", "title": "Slow episode"},
            delay=1.0,
        )
        db = FakeDB(runs=[])
        srv = DashboardServer(db=db, pipeline_module=pm,
                              cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")
        time.sleep(0.1)
        s, st = _get(f"{base}/api/run/status")
        assert s == 200
        assert st["status"] == "running"
        assert "stages" in st
        assert st.get("total_stages", 0) > 0
        srv.shutdown()

    # -- 7. Result interpretation --------------------------------------------

    def test_no_episode_shows_completed_not_success(self):
        """Stub pipeline → no_episode → completed state, but not success wording."""
        db = FakeDB(runs=[])
        pm = _make_pipeline({"status": "no_episode", "reason": "no_candidates"})
        srv = DashboardServer(db=db, pipeline_module=pm,
                              cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")
        for _ in range(30):
            _, st = _get(f"{base}/api/run/status")
            if st["status"] in ("completed", "failed"):
                break
            time.sleep(0.3)

        assert st["status"] == "completed", f"Expected completed, got {st['status']}"
        assert "no episode" in st.get("message", "").lower()
        assert "successful" not in st.get("message", "").lower()
        srv.shutdown()

    def test_success_shows_completed_with_title(self):
        """Successful pipeline → completed, shows title in message."""
        db = FakeDB(runs=[])
        pm = _make_pipeline({"status": "success", "title": "Episode 42"})
        srv = DashboardServer(db=db, pipeline_module=pm,
                              cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")
        for _ in range(30):
            _, st = _get(f"{base}/api/run/status")
            if st["status"] in ("completed", "failed"):
                break
            time.sleep(0.3)

        assert st["status"] == "completed"
        assert "Episode 42" in st["message"]
        srv.shutdown()

    def test_exception_shows_failed(self):
        """Pipeline exception → failed with error message."""
        db = FakeDB(runs=[])
        pm = _make_broken_pipeline(ConnectionError("network unreachable"))
        srv = DashboardServer(db=db, pipeline_module=pm,
                              cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"

        _post(f"{base}/api/cron/run")
        for _ in range(30):
            _, st = _get(f"{base}/api/run/status")
            if st["status"] in ("completed", "failed"):
                break
            time.sleep(0.3)

        assert st["status"] == "failed"
        assert "network unreachable" in st["message"]
        srv.shutdown()

    # -- 8. 404 --------------------------------------------------------------

    def test_unknown_path_returns_404(self):
        try:
            _get(f"{self.base}/nonexistent")
            assert False, "should have raised"
        except HTTPError as e:
            assert e.code == 404

    # -- 9. Shutdown ---------------------------------------------------------

    def test_shutdown_returns_within_timeout(self):
        srv = DashboardServer(db=FakeDB(), cron_service=FakeCronService(),
                              host="127.0.0.1", port=0)
        threading.Thread(target=srv.serve_forever,
                         kwargs={"poll_interval": 0.5}, daemon=True).start()
        time.sleep(0.2)

        done = threading.Event()
        threading.Thread(target=lambda: (srv.shutdown(), done.set()),
                         daemon=True).start()
        assert done.wait(timeout=2), "shutdown() deadlocked"
