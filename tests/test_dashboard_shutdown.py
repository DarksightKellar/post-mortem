"""Tests for the dashboard shutdown handler."""

import threading
import time
import unittest

from reddit_automation.dashboard.server import DashboardServer


class FakePipelineModule:
    def run_daily_pipeline(self, progress_callback=None):
        return {"status": "no_episode", "reason": "no_candidates"}


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


class TestDashboardShutdown(unittest.TestCase):
    """Verify that Ctrl+C / shutdown returns cleanly without deadlocking."""

    def test_shutdown_returns_within_timeout(self):
        """serve_forever() blocks in select(). shutdown() must wake it up and return."""
        server = DashboardServer(
            db=FakeDB(),
            cron_service=FakeCronService(),
            host="127.0.0.1",
            port=0,
        )

        # Run serve_forever in a background thread (same pattern as real usage)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        # Give the server time to bind and enter select()
        time.sleep(0.1)
        self.assertTrue(thread.is_alive())

        # Trigger shutdown from another thread and measure how long it takes
        done = threading.Event()
        start = time.time()

        def do_shutdown():
            server.shutdown()
            done.set()

        t = threading.Thread(target=do_shutdown, daemon=True)
        t.start()

        # shutdown() should return within 2 seconds.  If serve_forever is
        # blocked in select() with no timeout, it can hang forever.
        finished = done.wait(timeout=2)
        self.assertTrue(finished, f"shutdown() deadlocked after {time.time() - start:.1f}s")


if __name__ == "__main__":
    unittest.main()
