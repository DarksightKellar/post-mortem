from __future__ import annotations

from reddit_automation.pipeline import fetch as fetch_module
from reddit_automation.pipeline.fetch import fetch_candidates
from reddit_automation.storage.db import Database
from reddit_automation.storage.source_queue import SourceQueueRepository


SCHEMA_PATH = "data/schema.sql"


def test_fetch_candidates_claims_source_queue_and_marks_items_done(tmp_path, monkeypatch):
    db_path = tmp_path / "queue-fetch.db"
    db = Database(db_path)
    db.init_schema(SCHEMA_PATH)
    repo = SourceQueueRepository(db)
    reddit_item = repo.enqueue_url("https://www.reddit.com/r/tifu/comments/abc123/title/")
    bluesky_item = repo.enqueue_url("https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i")
    seen_configs = []

    class FakeRedditClient:
        def __init__(self, config):
            seen_configs.append(("reddit", config))

        def fetch(self):
            return [{"candidate_id": "reddit:abc123"}]

    class FakeBlueskyClient:
        def __init__(self, config):
            seen_configs.append(("bluesky", config))

        def fetch(self):
            return [{"candidate_id": "bluesky:at://did:plc:example/app.bsky.feed.post/3lqv2pprabs2i"}]

    monkeypatch.setattr(fetch_module, "RedditClient", FakeRedditClient)
    monkeypatch.setattr(fetch_module, "BlueskyClient", FakeBlueskyClient)

    candidates = fetch_candidates(
        {
            "sources": {"source_mode": "queue", "queue_limit": 10},
            "storage": {"db_path": str(db_path), "schema_path": SCHEMA_PATH},
        }
    )

    assert [candidate["candidate_id"] for candidate in candidates] == [
        "reddit:abc123",
        "bluesky:at://did:plc:example/app.bsky.feed.post/3lqv2pprabs2i",
    ]
    assert seen_configs[0][1]["sources"] == {
        "source_mode": "post_urls",
        "reddit_post_urls": ["https://www.reddit.com/r/tifu/comments/abc123/title/"],
    }
    assert seen_configs[1][1]["sources"] == {
        "source_mode": "bluesky",
        "bluesky_post_urls": ["https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i"],
    }

    with db.connect() as conn:
        rows = conn.execute("SELECT id, status, candidate_id FROM source_queue ORDER BY id").fetchall()

    assert [(row["id"], row["status"], row["candidate_id"]) for row in rows] == [
        (reddit_item["id"], "done", "reddit:abc123"),
        (bluesky_item["id"], "done", "bluesky:at://did:plc:example/app.bsky.feed.post/3lqv2pprabs2i"),
    ]


def test_fetch_candidates_marks_queue_item_failed_when_source_fetch_fails(tmp_path, monkeypatch):
    db_path = tmp_path / "queue-fetch.db"
    db = Database(db_path)
    db.init_schema(SCHEMA_PATH)
    repo = SourceQueueRepository(db)
    item = repo.enqueue_url("https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i")

    class FailingBlueskyClient:
        def __init__(self, config):
            pass

        def fetch(self):
            raise RuntimeError("HTTP 429")

    monkeypatch.setattr(fetch_module, "BlueskyClient", FailingBlueskyClient)

    candidates = fetch_candidates(
        {
            "sources": {"source_mode": "queue", "queue_limit": 10},
            "storage": {"db_path": str(db_path), "schema_path": SCHEMA_PATH},
        }
    )

    assert candidates == []
    with db.connect() as conn:
        row = conn.execute("SELECT id, status, error_message, attempts FROM source_queue").fetchone()

    assert row["id"] == item["id"]
    assert row["status"] == "failed"
    assert row["error_message"] == "HTTP 429"
    assert row["attempts"] == 1
