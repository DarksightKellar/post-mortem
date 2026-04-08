"""Dashboard HTTP server — serves HTML UI + JSON API for the pipeline."""

import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


HTML_TEMPLATE = Path(__file__).parent / "template.html"


class DashboardServer(HTTPServer):
    """HTTP dashboard with stats, run history, config viewer, and cron controls."""

    def __init__(self, db=None, pipeline_module=None, cron_service=None, host="127.0.0.1", port=8888):
        from reddit_automation.storage.runs import RunLogRepository

        self.db = db
        self.config_path = db.db_path if db else None
        self.run_logs = RunLogRepository(db) if db else None
        self.pipeline_module = pipeline_module
        self.cron_service = cron_service
        self._lock = threading.Lock()
        self._run_state: dict = {"status": "idle"}
        super().__init__((host, port), lambda *args, **kw: DashboardHandler(*args, server=self, **kw))

    def set_run_state(self, state: dict) -> None:
        with self._lock:
            self._run_state = state

    def get_run_state(self) -> dict:
        with self._lock:
            return dict(self._run_state)


class DashboardHandler(SimpleHTTPRequestHandler):
    """Handles dashboard routes."""

    def __init__(self, *args, server=None, **kwargs):
        self._dashboard_server = server
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send_html()
        elif self.path == "/api/stats":
            self._send_json(self._get_stats())
        elif self.path == "/api/runs" or self.path.startswith("/api/runs"):
            limit = 50
            if "limit=" in self.path:
                try:
                    limit = int(self.path.split("limit=")[1].split("&")[0])
                except (ValueError, IndexError):
                    pass
            self._send_json(self._get_runs(limit=limit))
        elif self.path == "/api/config" or self.path == "/api/config/":
            self._send_json(self._get_config())
        elif self.path == "/api/cron":
            self._send_json(self._get_cron())
        elif self.path == "/api/run/status":
            self._send_json(self._get_run_status())
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(content_length).decode()) if content_length else {}

        if self.path == "/api/config/update":
            self._send_json(self._update_config(body))
        elif self.path == "/api/cron/toggle":
            self._send_json(self._toggle_cron())
        elif self.path == "/api/cron/run":
            self._send_json(self._trigger_run())
        else:
            self.send_error(404)

    def _send_html(self):
        if HTML_TEMPLATE.exists():
            html = HTML_TEMPLATE.read_text()
        else:
            html = "<h1>Dashboard template not found</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_runs(self, limit=50):
        srv = self._dashboard_server
        if not srv or not srv.run_logs:
            return []
        try:
            return srv.run_logs.get_recent(limit=limit)
        except Exception as exc:
            return [{"error": str(exc)}]

    def _get_stats(self):
        runs = self._get_runs()
        total = len(runs)
        successes = sum(1 for r in runs if r.get("status") == "success")
        return {
            "total_runs": total,
            "success_rate": round((successes / total * 100) if total else 0, 1),
            "last_7_days": total,
        }

    def _get_config(self):
        try:
            from reddit_automation.utils.config import load_yaml_file
            from reddit_automation.utils.paths import CONFIG_DIR
            import json
            path = CONFIG_DIR / "config.yaml"
            data = load_yaml_file(path)
            return data
        except Exception as exc:
            return {"error": str(exc)}

    def _update_config(self, updates):
        try:
            import yaml
            from reddit_automation.utils.paths import CONFIG_DIR

            ALLOWED_KEYS = {
                "project", "sources", "filters", "comments", "scoring",
                "hosts", "prompts", "scripting", "render", "publishing",
                "alerts", "retry", "youtube",
            }

            unauthorized = set(updates.keys()) - ALLOWED_KEYS
            if unauthorized:
                return {"error": f"Unauthorized config keys: {sorted(unauthorized)}"}

            path = CONFIG_DIR / "config.yaml"
            with open(path, "r") as f:
                current = yaml.safe_load(f) or {}

            current.update(updates)
            with open(path, "w") as f:
                yaml.dump(current, f, default_flow_style=False)

            return {"status": "updated"}
        except Exception as exc:
            return {"error": str(exc)}

    def _get_cron(self):
        srv = self._dashboard_server
        if not srv or not srv.cron_service:
            return {"enabled": False, "message": "Cron not connected"}
        return srv.cron_service.get_status()

    def _toggle_cron(self):
        srv = self._dashboard_server
        if not srv or not srv.cron_service:
            return {"error": "Cron not connected"}
        return srv.cron_service.toggle()

    def _run_cron(self):
        srv = self._dashboard_server
        if not srv or not srv.cron_service:
            return {"error": "Cron not connected"}
        return srv.cron_service.run_now()

    def _get_run_status(self):
        srv = self._dashboard_server
        if not srv:
            return {"status": "idle"}
        return srv.get_run_state()

    def _trigger_run(self):
        srv = self._dashboard_server
        if not srv or not srv.pipeline_module:
            return {"error": "Pipeline module not connected"}

        current = srv.get_run_state()
        if current.get("status") == "running":
            return {"error": "Pipeline already running"}

        STAGES = ["fetch", "filter", "store", "score", "select",
                   "outline", "script", "voice", "visuals", "render", "publish"]

        def progress_callback(status: str, stage: str, message: str) -> None:
            state = srv.get_run_state()
            stage_order = {s: i for i, s in enumerate(STAGES)}
            state["status"] = "running"
            state["stage"] = stage
            state["stage_index"] = stage_order.get(stage, -1)
            state["total_stages"] = len(STAGES)
            state["message"] = message
            state.setdefault("stages", {})
            state["stages"][stage] = {"status": status}
            srv.set_run_state(state)

        def run_in_thread():
            try:
                srv.set_run_state({
                    "status": "running",
                    "stage": "fetch",
                    "stage_index": 0,
                    "total_stages": len(STAGES),
                    "message": "Starting pipeline\u2026",
                    "stages": {s: {"status": "pending"} for s in STAGES},
                    "started_at": time.time(),
                })

                result = srv.pipeline_module.run_daily_pipeline(
                    progress_callback=progress_callback
                )

                state = srv.get_run_state()

                # Interpret the pipeline result — distinguish real success from non-results
                if result.get("status") == "no_episode":
                    state["status"] = "completed"
                    state["message"] = "No episode generated: no items passed selection"
                    state["completed_at"] = time.time()
                elif result.get("status") == "success":
                    state["status"] = "completed"
                    state["message"] = f"Completed: {result.get('title', 'pipeline finished')}"
                    state["completed_at"] = time.time()
                else:
                    state["status"] = "failed"
                    state["message"] = f"Pipeline returned unexpected result: {result.get('status', type(result).__name__)}"
                    state["completed_at"] = time.time()

                state["result"] = str(result)
                srv.set_run_state(state)
            except Exception as exc:
                state = srv.get_run_state()
                state["status"] = "failed"
                state["message"] = f"Failed at {state.get('stage', 'unknown')}: {exc}"
                state["error"] = str(exc)
                state["completed_at"] = time.time()
                srv.set_run_state(state)

        t = threading.Thread(target=run_in_thread, daemon=True)
        t.start()
        return {"status": "started", "message": "Pipeline started"}

    def log_message(self, format, *args):
        pass


def run_dashboard(host="127.0.0.1", port=8888):
    """Start the dashboard server. Blocks until interrupted."""
    import signal
    import sys

    # Auto-clear stale .pyc bytecode on startup to prevent phantom tracebacks.
    root = Path(__file__).resolve().parent.parent.parent
    for pyc in root.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    for cache in root.rglob("__pycache__"):
        if not any(cache.iterdir()):
            cache.rmdir()

    from reddit_automation.pipeline import run_daily as pipeline_module
    from reddit_automation.dashboard.cron import CronService
    from reddit_automation.storage.bootstrap import bootstrap_database
    from reddit_automation.utils.config import load_config

    config = load_config()
    db = bootstrap_database(config)
    cron_service = CronService(pipeline_module=pipeline_module, db=db)
    cron_service.start()

    server = DashboardServer(
        db=db,
        pipeline_module=pipeline_module,
        cron_service=cron_service,
        host=host,
        port=port,
    )
    print(f"Dashboard running at http://{host}:{port}")

    _stop = False

    def _shutdown(sig, frame):
        nonlocal _stop
        print("\nShutting down dashboard\u2026")
        cron_service.stop()
        _stop = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Simple request loop — no serve_forever deadlock.
    # Blocks briefly on each request, then checks _stop flag.
    server.timeout = 0.5
    while not _stop:
        server.handle_request()

    sys.exit(0)


if __name__ == "__main__":
    run_dashboard()
