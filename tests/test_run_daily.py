import json
import sqlite3

import pytest

from reddit_automation.pipeline import run_daily as run_daily_module


RUN_DAILY_TEST_SCHEMA = """
CREATE TABLE reddit_candidates (
    reddit_post_id TEXT PRIMARY KEY,
    subreddit TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    author TEXT,
    created_utc INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE candidate_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reddit_post_id TEXT NOT NULL,
    comment_id TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    author TEXT,
    created_utc INTEGER
);
CREATE TABLE run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def write_test_schema(schema_path):
    schema_path.write_text(RUN_DAILY_TEST_SCHEMA, encoding="utf-8")


def test_run_daily_pipeline_stores_only_filtered_survivors(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        },
        "filters": {
            "exclude_categories": ["nsfw"],
            "exclude_low_context": True,
            "dedupe_similar_posts": True,
        },
    }

    raw_candidates = [
        {
            "reddit_post_id": "keep-1",
            "subreddit": "AskReddit",
            "title": "Office lunch disaster",
            "body": "Someone microwaved fish and everyone panicked.",
            "url": "https://reddit.com/r/AskReddit/comments/keep1",
            "author": "user1",
            "created_utc": 1712345000,
            "score": 500,
            "comment_count": 12,
            "raw_json": {"id": "keep-1"},
            "top_comments": [],
        },
        {
            "reddit_post_id": "drop-1",
            "subreddit": "tifu",
            "title": "This turned into porn somehow",
            "body": "",
            "url": "https://reddit.com/r/tifu/comments/drop1",
            "author": "user2",
            "created_utc": 1712345001,
            "score": 50,
            "comment_count": 2,
            "raw_json": {"id": "drop-1"},
            "top_comments": [],
        },
    ]

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", lambda _config: raw_candidates, raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "select_episode_items", lambda _candidates, _config: {}, raising=False)
    monkeypatch.setattr(
        run_daily_module,
        "build_episode_outline",
        lambda _selected, _config: {"episode_date": "2026-04-03"},
        raising=False,
    )
    monkeypatch.setattr(run_daily_module, "write_episode_script", lambda _outline, _config: {"title": ""}, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", lambda _script, _config: "", raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", lambda _outline, _config: {}, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", lambda _audio_path, _visual_plan, _config: "", raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", lambda _video_path, _metadata, _config: {}, raising=False)

    run_daily_module.run_daily_pipeline()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT reddit_post_id FROM reddit_candidates ORDER BY reddit_post_id"
        ).fetchall()

    assert rows == [("keep-1",)]


def test_run_daily_pipeline_stores_comments_for_surviving_candidates(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        },
        "filters": {
            "exclude_categories": ["nsfw"],
            "exclude_low_context": True,
            "dedupe_similar_posts": True,
        },
    }

    raw_candidates = [
        {
            "reddit_post_id": "keep-1",
            "subreddit": "AskReddit",
            "title": "Office lunch disaster",
            "body": "Someone microwaved fish and everyone panicked.",
            "url": "https://reddit.com/r/AskReddit/comments/keep1",
            "author": "user1",
            "created_utc": 1712345000,
            "score": 500,
            "comment_count": 12,
            "raw_json": {"id": "keep-1"},
            "top_comments": [
                {
                    "comment_id": "c-keep-1",
                    "body": "This is now a seafood emergency.",
                    "score": 44,
                    "author": "commenter1",
                    "created_utc": 1712345010,
                }
            ],
        },
        {
            "reddit_post_id": "drop-1",
            "subreddit": "tifu",
            "title": "This turned into porn somehow",
            "body": "",
            "url": "https://reddit.com/r/tifu/comments/drop1",
            "author": "user2",
            "created_utc": 1712345001,
            "score": 50,
            "comment_count": 2,
            "raw_json": {"id": "drop-1"},
            "top_comments": [
                {
                    "comment_id": "c-drop-1",
                    "body": "Nope.",
                    "score": 3,
                    "author": "commenter2",
                    "created_utc": 1712345011,
                }
            ],
        },
    ]

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", lambda _config: raw_candidates, raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "select_episode_items", lambda _candidates, _config: {}, raising=False)
    monkeypatch.setattr(
        run_daily_module,
        "build_episode_outline",
        lambda _selected, _config: {"episode_date": "2026-04-03"},
        raising=False,
    )
    monkeypatch.setattr(run_daily_module, "write_episode_script", lambda _outline, _config: {"title": ""}, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", lambda _script, _config: "", raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", lambda _outline, _config: {}, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", lambda _audio_path, _visual_plan, _config: "", raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", lambda _video_path, _metadata, _config: {}, raising=False)

    run_daily_module.run_daily_pipeline()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT reddit_post_id, comment_id, body, score, author, created_utc
            FROM candidate_comments
            ORDER BY comment_id
            """
        ).fetchall()

    assert rows == [
        (
            "keep-1",
            "c-keep-1",
            "This is now a seafood emergency.",
            44,
            "commenter1",
            1712345010,
        )
    ]


def test_run_daily_pipeline_orchestrates_media_path_through_publish(monkeypatch):
    config = {
        "project": {
            "final_pick_count": 1,
            "backup_pick_count": 1,
            "render_dir": "/tmp/renders",
        },
        "scripting": {"target_segments": 1},
    }
    db = object()
    raw_candidates = [{"reddit_post_id": "raw-1"}]
    filtered_candidates = [{"reddit_post_id": "filtered-1"}]
    scored_candidates = [{"reddit_post_id": "scored-1", "keep": True}]
    selected_items = {"primary": [{"reddit_post_id": "selected-1"}], "backups": []}
    outline = {"episode_date": "2026-04-03", "segments": [{"position": 1}], "title_angle": "Angle"}
    script = {"title": "Episode Title", "segments": [{"position": 1}]}
    audio_path = "/tmp/audio/episode.wav"
    visual_plan = {"episode_date": "2026-04-03", "scenes": [{"type": "segment"}]}
    video_path = "/tmp/renders/2026-04-03.mp4"
    publish_result = {"video_id": "abc123"}
    calls = []
    logged_entries = []
    notifications = []

    class StubRunLogRepository:
        def __init__(self, received_db):
            assert received_db is db
            calls.append(("RunLogRepository", received_db))

        def log(self, run_date, stage, status, message, payload=None):
            logged_entries.append(
                {
                    "run_date": run_date,
                    "stage": stage,
                    "status": status,
                    "message": message,
                    "payload": payload,
                }
            )

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config)

    def fake_bootstrap_database(received_config):
        assert received_config is config
        calls.append(("bootstrap_database", received_config))
        return db

    def fake_fetch_candidates(received_config):
        assert received_config is config
        calls.append(("fetch_candidates", received_config))
        return raw_candidates

    def fake_filter_candidates(received_candidates, received_config):
        assert received_candidates is raw_candidates
        assert received_config is config
        calls.append(("filter_candidates", received_candidates, received_config))
        return filtered_candidates

    def fake_store_candidates(received_candidates, received_db):
        assert received_candidates is filtered_candidates
        assert received_db is db
        calls.append(("store_candidates", received_candidates, received_db))

    def fake_score_candidates(received_candidates, received_config):
        assert received_candidates is filtered_candidates
        assert received_config is config
        calls.append(("score_candidates", received_candidates, received_config))
        return scored_candidates

    def fake_select_episode_items(received_candidates, received_config):
        assert received_candidates is scored_candidates
        assert received_config is config
        calls.append(("select_episode_items", received_candidates, received_config))
        return selected_items

    def fake_build_episode_outline(received_items, received_config):
        assert received_items is selected_items
        assert received_config is config
        calls.append(("build_episode_outline", received_items, received_config))
        return outline

    def fake_write_episode_script(received_outline, received_config):
        assert received_outline is outline
        assert received_config is config
        calls.append(("write_episode_script", received_outline, received_config))
        return script

    def fake_generate_episode_audio(received_script, received_config):
        assert received_script is script
        assert received_config is config
        calls.append(("generate_episode_audio", received_script, received_config))
        return audio_path

    def fake_build_visual_plan(received_outline, received_config):
        assert received_outline is outline
        assert received_config is config
        calls.append(("build_visual_plan", received_outline, received_config))
        return visual_plan

    def fake_render_episode_video(received_audio_path, received_visual_plan, received_config):
        assert received_audio_path == audio_path
        assert received_visual_plan is visual_plan
        assert received_config is config
        calls.append(("render_episode_video", received_audio_path, received_visual_plan, received_config))
        return video_path

    def fake_publish_episode(received_video_path, received_metadata, received_config):
        assert received_video_path == video_path
        assert received_metadata == {"title": script["title"]}
        assert received_config is config
        calls.append(("publish_episode", received_video_path, received_metadata, received_config))
        return publish_result

    monkeypatch.setattr(run_daily_module, "bootstrap_database", fake_bootstrap_database)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", fake_fetch_candidates)
    monkeypatch.setattr(run_daily_module, "filter_candidates", fake_filter_candidates)
    monkeypatch.setattr(run_daily_module, "store_candidates", fake_store_candidates)
    monkeypatch.setattr(run_daily_module, "score_candidates", fake_score_candidates, raising=False)
    monkeypatch.setattr(run_daily_module, "select_episode_items", fake_select_episode_items, raising=False)
    monkeypatch.setattr(run_daily_module, "build_episode_outline", fake_build_episode_outline, raising=False)
    monkeypatch.setattr(run_daily_module, "write_episode_script", fake_write_episode_script, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", fake_generate_episode_audio, raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", fake_build_visual_plan, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", fake_render_episode_video, raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", fake_publish_episode, raising=False)
    monkeypatch.setattr(run_daily_module, "RunLogRepository", StubRunLogRepository, raising=False)
    monkeypatch.setattr(
        run_daily_module,
        "send_run_notification",
        lambda status, message, received_config: notifications.append((status, message, received_config)),
        raising=False,
    )

    result = run_daily_module.run_daily_pipeline()

    assert result == {
        "status": "success",
        "run_date": outline["episode_date"],
        "title": script["title"],
        "video_path": video_path,
        "publish_result": publish_result,
    }
    assert calls == [
        ("bootstrap_database", config),
        ("RunLogRepository", db),
        ("fetch_candidates", config),
        ("filter_candidates", raw_candidates, config),
        ("store_candidates", filtered_candidates, db),
        ("score_candidates", filtered_candidates, config),
        ("select_episode_items", scored_candidates, config),
        ("build_episode_outline", selected_items, config),
        ("write_episode_script", outline, config),
        ("generate_episode_audio", script, config),
        ("build_visual_plan", outline, config),
        ("render_episode_video", audio_path, visual_plan, config),
        ("publish_episode", video_path, {"title": script["title"]}, config),
    ]
    assert logged_entries == [
        {
            "run_date": outline["episode_date"],
            "stage": "publish",
            "status": "success",
            "message": "Episode published successfully",
            "payload": {
                "title": script["title"],
                "video_path": video_path,
                "publish_result": publish_result,
            },
        }
    ]
    assert notifications == [
        ("success", f"Episode published successfully: {script['title']}", config)
    ]


def test_run_daily_pipeline_returns_no_episode_when_selection_is_empty(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }
    outline_calls = []
    script_calls = []
    voice_calls = []
    visuals_calls = []
    render_calls = []
    publish_calls = []
    notifications = []

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", lambda _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "filter_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(
        run_daily_module,
        "select_episode_items",
        lambda _candidates, _config: {"primary": [], "backups": []},
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "build_episode_outline",
        lambda _selected, _config: outline_calls.append((_selected, _config)),
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "write_episode_script",
        lambda _outline, _config: script_calls.append((_outline, _config)),
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "generate_episode_audio",
        lambda _script, _config: voice_calls.append((_script, _config)),
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "build_visual_plan",
        lambda _outline, _config: visuals_calls.append((_outline, _config)),
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "render_episode_video",
        lambda _audio_path, _visual_plan, _config: render_calls.append((_audio_path, _visual_plan, _config)),
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "publish_episode",
        lambda _video_path, _metadata, _config: publish_calls.append((_video_path, _metadata, _config)),
        raising=False,
    )
    monkeypatch.setattr(
        run_daily_module,
        "send_run_notification",
        lambda status, message, received_config: notifications.append((status, message, received_config)),
        raising=False,
    )

    result = run_daily_module.run_daily_pipeline()

    assert outline_calls == []
    assert script_calls == []
    assert voice_calls == []
    assert visuals_calls == []
    assert render_calls == []
    assert publish_calls == []
    assert notifications == [
        ("success", "No episode generated: no selected items", config)
    ]
    assert result == {
        "status": "no_episode",
        "reason": "no_selected_items",
    }

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_date, stage, status, message, payload_json
            FROM run_logs
            ORDER BY id
            """
        ).fetchall()

    assert rows == [
        (
            "unknown",
            "select",
            "success",
            "No episode generated",
            json.dumps({"reason": "no_selected_items"}),
        )
    ]


def test_run_daily_pipeline_logs_final_publish_result(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }
    outline = {"episode_date": "2026-04-03", "segments": []}
    script = {"title": "Episode Title", "segments": []}
    video_path = "/tmp/renders/2026-04-03.mp4"
    publish_result = {"video_id": "abc123", "url": "https://example.com/watch?v=abc123"}

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", lambda _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "filter_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(
        run_daily_module,
        "select_episode_items",
        lambda _candidates, _config: {"primary": [{"reddit_post_id": "selected-1"}], "backups": []},
        raising=False,
    )
    monkeypatch.setattr(run_daily_module, "build_episode_outline", lambda _selected, _config: outline, raising=False)
    monkeypatch.setattr(run_daily_module, "write_episode_script", lambda _outline, _config: script, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", lambda _script, _config: "/tmp/audio/episode.wav", raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", lambda _outline, _config: {"scenes": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", lambda _audio_path, _visual_plan, _config: video_path, raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", lambda _video_path, _metadata, _config: publish_result, raising=False)

    result = run_daily_module.run_daily_pipeline()

    assert result == {
        "status": "success",
        "run_date": outline["episode_date"],
        "title": script["title"],
        "video_path": video_path,
        "publish_result": publish_result,
    }

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_date, stage, status, message, payload_json
            FROM run_logs
            ORDER BY id
            """
        ).fetchall()

    assert rows == [
        (
            outline["episode_date"],
            "publish",
            "success",
            "Episode published successfully",
            json.dumps(
                {
                    "title": script["title"],
                    "video_path": video_path,
                    "publish_result": publish_result,
                }
            ),
        )
    ]


def test_run_daily_pipeline_logs_failure_and_reraises_exception(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }
    outline = {"episode_date": "2026-04-03", "segments": []}
    script = {"title": "Episode Title", "segments": []}
    event_order = []

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", lambda _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "filter_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _candidates, _config: [], raising=False)
    monkeypatch.setattr(
        run_daily_module,
        "select_episode_items",
        lambda _candidates, _config: {"primary": [{"reddit_post_id": "selected-1"}], "backups": []},
        raising=False,
    )
    monkeypatch.setattr(run_daily_module, "build_episode_outline", lambda _selected, _config: outline, raising=False)
    monkeypatch.setattr(run_daily_module, "write_episode_script", lambda _outline, _config: script, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", lambda _script, _config: "/tmp/audio/episode.wav", raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", lambda _outline, _config: {"scenes": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", lambda _audio_path, _visual_plan, _config: "/tmp/renders/2026-04-03.mp4", raising=False)

    original_repository = run_daily_module.RunLogRepository

    class TrackingRunLogRepository(original_repository):
        def log(self, run_date, stage, status, message, payload=None):
            event_order.append(("log", status, message))
            return super().log(run_date, stage, status, message, payload)

    def raise_publish_error(_video_path, _metadata, _config):
        raise RuntimeError("upload failed")

    def fake_send_run_notification(status, message, received_config):
        event_order.append(("notify", status, message, received_config))

    monkeypatch.setattr(run_daily_module, "RunLogRepository", TrackingRunLogRepository, raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", raise_publish_error, raising=False)
    monkeypatch.setattr(run_daily_module, "send_run_notification", fake_send_run_notification, raising=False)

    with pytest.raises(RuntimeError, match="upload failed"):
        run_daily_module.run_daily_pipeline()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_date, stage, status, message, payload_json
            FROM run_logs
            ORDER BY id
            """
        ).fetchall()

    assert rows == [
        (
            outline["episode_date"],
            "publish",
            "failure",
            "upload failed",
            json.dumps({"error_type": "RuntimeError"}),
        )
    ]
    assert event_order == [
        ("log", "failure", "upload failed"),
        ("notify", "failure", "upload failed", config),
    ]


def test_run_daily_pipeline_retries_on_transient_fetch_error(tmp_path, monkeypatch):
    """Pipeline retries fetch_candidates when it fails transiently, then succeeds."""
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        },
        "filters": {
            "exclude_categories": ["nsfw"],
            "exclude_low_content": True,
            "dedupe_similar_posts": True,
        },
        "retry": {
            "max_retries": 3,
            "base_delay": 0.01,
        },
    }

    fetch_calls = [0]

    def flaky_fetch(_config):
        fetch_calls[0] += 1
        if fetch_calls[0] < 3:
            raise ConnectionError("transient network error")
        return [
            {
                "reddit_post_id": "recovered-1",
                "subreddit": "AskReddit",
                "title": "Recovered after retries",
                "body": "This survived",
                "url": "https://reddit.com/r/AskReddit/comments/recovered1",
                "author": "user1",
                "created_utc": 1712345000,
                "score": 500,
                "comment_count": 12,
                "raw_json": {"id": "recovered-1"},
                "top_comments": [],
            }
        ]

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", flaky_fetch, raising=False)
    monkeypatch.setattr(run_daily_module, "filter_candidates", lambda c, _config: c, raising=False)
    monkeypatch.setattr(run_daily_module, "store_candidates", lambda _c, _db: None, raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _c, _config: [], raising=False)
    monkeypatch.setattr(run_daily_module, "select_episode_items", lambda _c, _config: {"primary": [{"reddit_post_id": "r1"}]}, raising=False)
    monkeypatch.setattr(run_daily_module, "build_episode_outline", lambda _s, _config: {"episode_date": "2026-04-03", "segments": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "write_episode_script", lambda _o, _config: {"title": "T", "segments": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", lambda _s, _config: "/tmp/ep.wav", raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", lambda _o, _config: {"scenes": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", lambda _a, _v, _config: "/tmp/ep.mp4", raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", lambda _v, _m, _config: {}, raising=False)
    monkeypatch.setattr(run_daily_module, "send_run_notification", lambda _s, _m, _c: None, raising=False)

    result = run_daily_module.run_daily_pipeline()

    assert fetch_calls[0] == 3
    assert result["status"] == "success"


def test_run_daily_pipeline_retries_render_on_transient_error(tmp_path, monkeypatch):
    """Pipeline retries render_episode_video when it fails transiently, then succeeds."""
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        },
        "filters": {
            "exclude_categories": ["nsfw"],
            "exclude_low_context": True,
            "dedupe_similar_posts": True,
        },
        "retry": {
            "max_retries": 3,
            "base_delay": 0.01,
        },
    }

    render_calls = [0]

    def flaky_render(_audio, _visual, _config):
        render_calls[0] += 1
        if render_calls[0] < 2:
            raise ConnectionError("ffmpeg connection timeout")
        return "/tmp/renders/2026-04-03.mp4"

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", lambda _config: [{"reddit_post_id": "r1"}], raising=False)
    monkeypatch.setattr(run_daily_module, "filter_candidates", lambda c, _config: c, raising=False)
    monkeypatch.setattr(run_daily_module, "store_candidates", lambda _c, _db: None, raising=False)
    monkeypatch.setattr(run_daily_module, "score_candidates", lambda _c, _config: [{"reddit_post_id": "r1", "keep": True}], raising=False)
    monkeypatch.setattr(run_daily_module, "select_episode_items", lambda _c, _config: {"primary": [{"reddit_post_id": "r1"}], "backups": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "build_episode_outline", lambda _s, _config: {"episode_date": "2026-04-03", "segments": [], "title_angle": "T"}, raising=False)
    monkeypatch.setattr(run_daily_module, "write_episode_script", lambda _o, _config: {"title": "T", "segments": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "generate_episode_audio", lambda _s, _config: "/tmp/audio.wav", raising=False)
    monkeypatch.setattr(run_daily_module, "build_visual_plan", lambda _o, _config: {"scenes": []}, raising=False)
    monkeypatch.setattr(run_daily_module, "render_episode_video", flaky_render, raising=False)
    monkeypatch.setattr(run_daily_module, "publish_episode", lambda _v, _m, _config: {}, raising=False)
    monkeypatch.setattr(run_daily_module, "send_run_notification", lambda _s, _m, _c: None, raising=False)

    result = run_daily_module.run_daily_pipeline()

    assert render_calls[0] == 2
    assert result["status"] == "success"


def test_run_daily_pipeline_fails_after_exhausting_retries(tmp_path, monkeypatch):
    """Pipeline gives up and raises after all retries are exhausted on fetch."""
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        },
        "filters": {
            "exclude_categories": ["nsfw"],
            "exclude_low_context": True,
            "dedupe_similar_posts": True,
        },
        "retry": {
            "max_retries": 3,
            "base_delay": 0.01,
        },
    }

    fetch_calls = [0]
    notify_calls = []

    def always_fail(_config):
        fetch_calls[0] += 1
        raise ConnectionError("permanent Reddit outage")

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config, raising=False)
    monkeypatch.setattr(run_daily_module, "fetch_candidates", always_fail, raising=False)
    monkeypatch.setattr(run_daily_module, "send_run_notification", lambda s, m, c: notify_calls.append((s, m)), raising=False)

    with pytest.raises(ConnectionError, match="permanent Reddit outage"):
        run_daily_module.run_daily_pipeline()

    # Should have tried max_retries times
    assert fetch_calls[0] == 3
    # Should have sent failure notification
    assert any(s == "failure" for s, _m in notify_calls)


def test_run_daily_pipeline_executes_real_end_to_end_flow_with_io_stubs(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    render_dir = tmp_path / "renders"
    assets_dir = tmp_path / "assets"
    output_dir = tmp_path / "output"
    write_test_schema(schema_path)

    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        },
        "project": {
            "episode_date": "2026-04-03",
            "final_pick_count": 3,
            "backup_pick_count": 2,
            "render_dir": str(render_dir),
            "assets_dir": str(assets_dir),
        },
        "comments": {
            "top_n_per_candidate": 5,
            "max_selected_comments_per_segment": 2,
        },
        "filters": {
            "exclude_categories": ["politics", "culture_war", "tragedy", "abuse", "death", "nsfw"],
            "exclude_low_context": True,
            "dedupe_similar_posts": True,
            "min_body_or_comment_signal": 1,
        },
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
            "host_1": {"key": "host_1", "name": "Host 1", "role": "main"},
            "host_2": {"key": "host_2", "name": "Host 2", "role": "adaptive"},
        },
        "scripting": {
            "target_segments": 3,
            "cold_open_seconds": 15,
            "outro_seconds": 40,
            "max_direct_quote_words": 12,
        },
        "render": {
            "resolution": "1920x1080",
            "fps": 30,
            "slide_style": "minimal",
        },
        "publishing": {
            "default_privacy_status": "private",
        },
        "alerts": {
            "telegram_on_success": True,
            "telegram_on_failure": True,
            "telegram_bot_token": "test-token",
            "telegram_chat_id": "test-chat",
        },
        "output_dir": str(output_dir),
        "reddit_test_data": {
            "submissions": [
                {
                    "id": "post-1",
                    "subreddit": "tifu",
                    "title": "TIFU by accidentally starting a neighbourhood war",
                    "selftext": "So this happened last weekend when I meant to compliment my neighbour's lawn.",
                    "url": "https://reddit.com/r/tifu/comments/post1",
                    "author": "user1",
                    "created_utc": 1712345000,
                    "score": 500,
                    "num_comments": 3,
                    "comments": [
                        {"id": "c1", "body": "This is hilarious.", "score": 200, "author": "commenter1", "created_utc": 1712345001},
                        {"id": "c2", "body": "The ending got me.", "score": 150, "author": "commenter2", "created_utc": 1712345002},
                        {"id": "c3", "body": "I had something similar happen.", "score": 80, "author": "commenter3", "created_utc": 1712345003},
                    ],
                },
                {
                    "id": "post-2",
                    "subreddit": "AmItheAsshole",
                    "title": "AITA for refusing to share my wifi password?",
                    "selftext": "My neighbour keeps asking for my wifi password and I keep saying no.",
                    "url": "https://reddit.com/r/AmItheAsshole/comments/post2",
                    "author": "user2",
                    "created_utc": 1712345100,
                    "score": 400,
                    "num_comments": 2,
                    "comments": [
                        {"id": "c4", "body": "NTA, it's your property.", "score": 120, "author": "commenter4", "created_utc": 1712345101},
                        {"id": "c5", "body": "Just get a guest network.", "score": 90, "author": "commenter5", "created_utc": 1712345102},
                    ],
                },
                {
                    "id": "post-3",
                    "subreddit": "MaliciousCompliance",
                    "title": "Boss said no overtime, so I left a project unfinished",
                    "selftext": "My manager said we're not allowed to work overtime, so I left at 5pm exactly.",
                    "url": "https://reddit.com/r/MaliciousCompliance/comments/post3",
                    "author": "user3",
                    "created_utc": 1712345200,
                    "score": 600,
                    "num_comments": 2,
                    "comments": [
                        {"id": "c6", "body": "Classic malicious compliance.", "score": 300, "author": "commenter6", "created_utc": 1712345201},
                        {"id": "c7", "body": "Management did this to themselves.", "score": 200, "author": "commenter7", "created_utc": 1712345202},
                    ],
                },
            ]
        },
    }

    tts_calls = []
    stitch_calls = []
    rendered_scene_prompts = []
    render_calls = []
    notification_requests = []

    monkeypatch.setattr(run_daily_module, "load_config", lambda: config)

    def stub_llm_complete(self, prompt_name, payload):
        assert prompt_name == "scoring"
        return {
            "reaction_potential": 10,
            "laugh_factor": 8,
            "story_payoff": 7,
            "clarity_after_rewrite": 9,
            "comment_bonus": 6,
        }

    def stub_tts_generate(self, speaker_key, text):
        tts_calls.append((speaker_key, text))
        path = tmp_path / f"{len(tts_calls):04d}-{speaker_key}.mp3"
        path.write_bytes(b"audio")
        return str(path)

    def stub_stitch_audio_clips(audio_paths, output_path):
        stitch_calls.append((audio_paths, output_path))
        output = tmp_path / "episode_audio.mp3"
        output.write_bytes(b"stitched-audio")
        return str(output)

    class StubFalClient:
        def __init__(self, api_key=None, config=None):
            self.config = config

        def generate(self, prompt, output_path, max_retries=30, poll_interval=2.0):
            rendered_scene_prompts.append(prompt)
            output_file = tmp_path / output_path.split("/")[-1]
            output_file.write_bytes(b"image")
            return str(output_file)

    def stub_render_video(*, audio_path, visual_plan, output_path, config, scene_images=None):
        render_calls.append(
            {
                "audio_path": audio_path,
                "visual_plan": visual_plan,
                "output_path": output_path,
                "scene_images": scene_images,
            }
        )

    class StubTelegramResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"ok": True}).encode("utf-8")

    def stub_urlopen(request):
        notification_requests.append(request)
        return StubTelegramResponse()

    monkeypatch.setattr("reddit_automation.clients.llm_client.LLMClient.complete_json", stub_llm_complete)
    monkeypatch.setattr("reddit_automation.clients.tts_client.TTSClient.generate", stub_tts_generate)
    monkeypatch.setattr("reddit_automation.pipeline.voice.stitch_audio_clips", stub_stitch_audio_clips)
    monkeypatch.setattr("reddit_automation.pipeline.generate_scenes.FalClient", StubFalClient)
    monkeypatch.setattr("reddit_automation.pipeline.render.render_video", stub_render_video)
    monkeypatch.setattr(
        run_daily_module,
        "publish_episode",
        lambda _video_path, _metadata, _config: {
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
            "status": "uploaded",
            "privacy_status": "private",
        },
    )
    monkeypatch.setattr("urllib.request.urlopen", stub_urlopen)

    result = run_daily_module.run_daily_pipeline()

    assert result["status"] == "success"
    assert result["run_date"] == "2026-04-03"
    assert result["publish_result"]["video_id"] == "abc123"
    assert tts_calls, "voice stage should synthesize dialogue"
    assert stitch_calls, "voice stage should stitch generated clips"
    assert rendered_scene_prompts, "render stage should generate scene prompts"
    assert render_calls[0]["scene_images"], "render stage should receive generated scene images"
    assert len(notification_requests) == 1

    with sqlite3.connect(db_path) as conn:
        candidate_ids = conn.execute(
            "SELECT reddit_post_id FROM reddit_candidates ORDER BY reddit_post_id"
        ).fetchall()
        run_log = conn.execute(
            "SELECT run_date, stage, status, message, payload_json FROM run_logs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert candidate_ids == [("post-1",), ("post-2",), ("post-3",)]
    assert run_log[0] == "2026-04-03"
    assert run_log[1] == "publish"
    assert run_log[2] == "success"
    assert json.loads(run_log[4])["publish_result"]["video_id"] == "abc123"
