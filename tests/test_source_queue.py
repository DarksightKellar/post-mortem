from __future__ import annotations

from reddit_automation.storage.db import Database
from reddit_automation.storage.source_queue import SourceQueueRepository


SCHEMA_PATH = "data/schema.sql"


def _repo(tmp_path):
    db = Database(tmp_path / "queue.db")
    db.init_schema(SCHEMA_PATH)
    return SourceQueueRepository(db)


def test_enqueue_url_derives_supported_sources(tmp_path):
    repo = _repo(tmp_path)

    reddit = repo.enqueue_url("https://www.reddit.com/r/tifu/comments/abc123/title/")
    bluesky = repo.enqueue_url("https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i")

    assert reddit["source"] == "reddit"
    assert bluesky["source"] == "bluesky"


def test_enqueue_url_dedupes_without_resetting_done_status(tmp_path):
    repo = _repo(tmp_path)
    first = repo.enqueue_url("https://www.reddit.com/r/tifu/comments/abc123/title/")
    repo.mark_done(first["id"], "reddit:abc123")

    second = repo.enqueue_url("https://www.reddit.com/r/tifu/comments/abc123/title/")

    assert second["id"] == first["id"]
    assert second["status"] == "done"
    assert repo.pending(limit=10) == []


def test_claim_pending_marks_oldest_items_processing(tmp_path):
    repo = _repo(tmp_path)
    first = repo.enqueue_url("https://www.reddit.com/r/tifu/comments/abc123/title/")
    repo.enqueue_url("https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i")

    claimed = repo.claim_pending(limit=1)

    assert [item["id"] for item in claimed] == [first["id"]]
    assert claimed[0]["status"] == "processing"
    assert [item["status"] for item in repo.pending(limit=10)] == ["pending"]


def test_mark_failed_keeps_error_and_makes_item_retryable(tmp_path):
    repo = _repo(tmp_path)
    item = repo.enqueue_url("https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i")

    failed = repo.mark_failed(item["id"], "HTTP 429")

    assert failed["status"] == "failed"
    assert failed["error_message"] == "HTTP 429"
    assert failed["attempts"] == 1
    assert repo.retry_failed(limit=10)[0]["id"] == item["id"]
