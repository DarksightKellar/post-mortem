"""Simple in-process cron scheduler for the pipeline."""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "data" / "cron_state.json"


class CronService:
    """Lightweight cron wrapper around `run_daily_pipeline`.

    Persists enabled/disabled state and last/next run timestamps
    to a JSON file so the setting survives dashboard restarts.
    Defaults to running once per day at the configured hour (UTC).
    """

    def __init__(self, pipeline_module, db=None, config_path: str = None):
        self.pipeline_module = pipeline_module
        self.db = db
        self.config_path = config_path
        self._timer: threading.Timer | None = None
        self._enabled = True
        self._schedule = None  # set after reading config
        self._load_state()

    # -- persistence ----------------------------------------------------------

    def _state_path(self) -> Path:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        return STATE_FILE

    def _load_state(self) -> None:
        if self._state_path().exists():
            try:
                data = json.loads(self._state_path().read_text())
                self._enabled = data.get("enabled", True)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self) -> None:
        self._state_path().write_text(json.dumps({
            "enabled": self._enabled,
            "last_run_at": getattr(self, "_last_run_at", None),
            "next_run_at": getattr(self, "_next_run_at", None),
        }, indent=2))

    # -- scheduling -----------------------------------------------------------

    def _read_schedule(self) -> str:
        """Return a cron-like string (e.g. '0 14 * * *') or interval like '24h'."""
        if self._schedule:
            return self._schedule
        # Read from config if available
        try:
            if self.config_path:
                cfg = json.loads(Path(self.config_path).read_text()) if Path(self.config_path).suffix == ".json" else {}
            else:
                cfg = {}
        except Exception:
            cfg = {}
        return cfg.get("cron", "0 14 * * *")  # default: daily at 14:00 UTC

    def _next_run_timestamp(self) -> float:
        """Calculate the next scheduled run time (epoch seconds)."""
        schedule = self._read_schedule()

        # Simple interval format like "24h" or "6h"
        if schedule.endswith("h"):
            try:
                hours = int(schedule[:-1])
            except ValueError:
                hours = 24
            return time.time() + hours * 3600

        # Default: every 24 hours
        return time.time() + 86400

    def _schedule_timer(self) -> None:
        """Schedule the next pipeline run."""
        if not self._enabled:
            return

        delay = self._next_run_timestamp() - time.time()
        if delay < 60:
            delay = 60  # minimum 1 minute

        self._next_run_at = datetime.fromtimestamp(
            time.time() + delay, tz=timezone.utc
        ).isoformat()
        self._save_state()

        self._timer = threading.Timer(delay, self._on_schedule)
        self._timer.daemon = True
        self._timer.start()

    def _on_schedule(self) -> None:
        """Called when the timer fires — run the pipeline then reschedule."""
        self._last_run_at = datetime.now(tz=timezone.utc).isoformat()
        self._save_state()
        if self.pipeline_module:
            threading.Thread(
                target=self.pipeline_module.run_daily_pipeline, daemon=True
            ).start()
        self._schedule_timer()

    # -- public API -----------------------------------------------------------

    def start(self) -> None:
        """Start the cron scheduler."""
        self._save_state()
        self._schedule_timer()

    def stop(self) -> None:
        """Stop the cron scheduler."""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def get_status(self) -> dict:
        return {
            "enabled": self._enabled,
            "next_run_at": getattr(self, "_next_run_at", None),
            "last_run_at": getattr(self, "_last_run_at", None),
            "schedule": self._read_schedule(),
        }

    def toggle(self) -> dict:
        self._enabled = not self._enabled
        self._save_state()

        if self._enabled:
            self._schedule_timer()
            action = "enabled"
        else:
            self.stop()
            action = "disabled"

        return {"enabled": self._enabled, "action": action}

    def run_now(self) -> dict:
        """Trigger a pipeline run immediately."""
        self._last_run_at = datetime.now(tz=timezone.utc).isoformat()
        self._save_state()
        t = threading.Thread(
            target=self.pipeline_module.run_daily_pipeline, daemon=True
        )
        t.start()
        return {"status": "triggered", "message": "Pipeline run queued"}
