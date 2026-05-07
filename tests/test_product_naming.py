from __future__ import annotations

import tomllib
from pathlib import Path


def test_postmortem_package_exposes_pipeline_imports():
    from postmortem.pipeline.fetch import fetch_candidates as product_fetch_candidates
    from reddit_automation.pipeline.fetch import fetch_candidates as legacy_fetch_candidates

    assert product_fetch_candidates is legacy_fetch_candidates


def test_postmortem_package_exposes_storage_imports():
    from postmortem.storage.source_queue import SourceQueueRepository as product_repo
    from reddit_automation.storage.source_queue import SourceQueueRepository as legacy_repo

    assert product_repo is legacy_repo


def test_postmortem_package_exposes_dashboard_imports():
    from postmortem.dashboard.server import DashboardServer as product_server
    from reddit_automation.dashboard.server import DashboardServer as legacy_server

    assert product_server is legacy_server


def test_project_description_is_source_neutral():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "postmortem"
    assert "Reddit-to-video" not in pyproject["project"]["description"]
    assert "multi-source" in pyproject["project"]["description"]


def test_postmortem_module_entrypoint_delegates_to_pipeline(monkeypatch):
    import postmortem.__main__ as entrypoint

    calls = []

    def fake_run_daily_pipeline():
        calls.append("ran")
        return {"status": "completed"}

    monkeypatch.setattr(entrypoint, "run_daily_pipeline", fake_run_daily_pipeline)

    assert entrypoint.main() == {"status": "completed"}
    assert calls == ["ran"]
