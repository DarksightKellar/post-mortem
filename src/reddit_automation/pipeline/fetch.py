from __future__ import annotations

from copy import deepcopy

from reddit_automation.clients.bluesky_client import BlueskyClient
from reddit_automation.clients.reddit_client import RedditClient
from reddit_automation.storage.db import Database
from reddit_automation.storage.source_queue import SourceQueueRepository
from reddit_automation.utils.paths import DB_PATH, SCHEMA_SQL_PATH


def fetch_candidates(config: dict) -> list[dict]:
    source_mode = config.get("sources", {}).get("source_mode")
    if source_mode == "queue":
        return _fetch_queued_candidates(config)
    if source_mode == "bluesky":
        return BlueskyClient(config).fetch()
    client = RedditClient(config)
    return client.fetch()


def _fetch_queued_candidates(config: dict) -> list[dict]:
    storage_config = config.get("storage", {})
    db = Database(storage_config.get("db_path") or DB_PATH)
    db.init_schema(storage_config.get("schema_path") or SCHEMA_SQL_PATH)
    repo = SourceQueueRepository(db)
    queue_limit = config.get("sources", {}).get("queue_limit", 10)

    candidates: list[dict] = []
    for item in repo.claim_pending(limit=queue_limit):
        try:
            fetched = _fetch_queue_item(config, item)
        except Exception as exc:  # noqa: BLE001 - queue items must record source-level fetch failures.
            repo.mark_failed(item["id"], str(exc))
            continue

        candidates.extend(fetched)
        candidate_id = fetched[0].get("candidate_id") if fetched else ""
        repo.mark_done(item["id"], candidate_id)
    return candidates


def _fetch_queue_item(config: dict, item: dict) -> list[dict]:
    item_config = deepcopy(config)
    if item["source"] == "reddit":
        item_config["sources"] = {
            "source_mode": "post_urls",
            "reddit_post_urls": [item["source_url"]],
        }
        return RedditClient(item_config).fetch()
    if item["source"] == "bluesky":
        item_config["sources"] = {
            "source_mode": "bluesky",
            "bluesky_post_urls": [item["source_url"]],
        }
        return BlueskyClient(item_config).fetch()
    raise ValueError(f"Unsupported queue source: {item['source']}")
