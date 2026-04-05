"""Dashboard HTTP server — serves HTML UI + JSON API for the pipeline."""

import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


HTML_TEMPLATE = Path(__file__).parent / "template.html"


class DashboardServer(HTTPServer):
    """HTTP dashboard with stats, run history, config viewer, and cron controls."""

    def __init__(self, db=None, pipeline_module=None, cron_service=None, host="127.0.0.1", port=8888):
        self.db = db
        self.pipeline_module = pipeline_module
        self.cron_service = cron_service
        self._lock = threading.Lock()
        super().__init__((host, port), lambda *args, **kw: DashboardHandler(*args, server=self, **kw))


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
            self._send_json(self._run_cron())
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
        if not srv or not srv.db:
            return []
        try:
            return srv.db.load_run_logs(limit=limit)
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
        srv = self._dashboard_server
        if not srv or not srv.db:
            return {}
        try:
            return srv.db.load_config()
        except Exception as exc:
            return {"error": str(exc)}

    def _update_config(self, updates):
        srv = self._dashboard_server
        if not srv or not srv.db:
            return {"error": "DB not connected"}

        # Whitelist of allowed top-level config keys
        ALLOWED_KEYS = {
            "project", "sources", "filters", "comments", "scoring",
            "hosts", "prompts", "scripting", "render", "publishing",
            "alerts", "retry", "youtube",
        }

        # Reject any keys not in the whitelist
        unauthorized = set(updates.keys()) - ALLOWED_KEYS
        if unauthorized:
            return {"error": f"Unauthorized config keys: {sorted(unauthorized)}"}

        try:
            return srv.db.update_config(updates)
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

    def log_message(self, format, *args):
        pass


def run_dashboard(host="127.0.0.1", port=8888, pipeline_module=None, cron_service=None):
    """Start the dashboard server. Blocks until interrupted."""
    import signal
    import sys

    server = DashboardServer(
        pipeline_module=pipeline_module,
        cron_service=cron_service,
        host=host,
        port=port,
    )
    print(f"Dashboard running at http://{host}:{port}")

    def _shutdown(sig, frame):
        print("\nShutting down dashboard…")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    server.serve_forever()


if __name__ == "__main__":
    run_dashboard()
