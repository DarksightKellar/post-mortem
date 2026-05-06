import re
from pathlib import Path

TEMPLATE_PATH = Path("/home/kel/projects/reddit-content-automation/src/reddit_automation/dashboard/template.html")


def test_index_html_has_hermes_like_shell_structure():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Shell containers inspired by the Hermes web UI (header + sidebar + main)
    assert "id=\"pm-shell\"" in html
    assert "id=\"pm-topbar\"" in html
    assert "id=\"pm-sidebar\"" in html
    assert "id=\"pm-main\"" in html

    # Navigation pages (pure HTML shell; we don't require URL routing)
    assert 'data-page="progress"' in html
    assert 'data-page="runs"' in html
    assert 'data-page="cron"' in html
    assert 'data-page="config"' in html

    # Preserve the backend contract hooks used by existing JS/tests.
    assert "const API = '/api';" in html
    assert "id=\"config-editor\"" in html
    assert "id=\"run-now-btn\"" in html
    assert "id=\"cron-toggle\"" in html


def test_sidebar_nav_items_present():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Lightweight structural assertions (avoid brittle CSS checks)
    for label in ["Pipeline", "Recent Runs", "Cron", "Config"]:
        assert label in html

    # Ensure we still have a polling section for the progress pipeline state
    assert re.search(r"id=\"progress-section\"", html) is not None
