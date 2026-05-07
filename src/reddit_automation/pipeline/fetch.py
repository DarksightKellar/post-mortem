from __future__ import annotations

from reddit_automation.clients.bluesky_client import BlueskyClient
from reddit_automation.clients.reddit_client import RedditClient


def fetch_candidates(config: dict) -> list[dict]:
    source_mode = config.get("sources", {}).get("source_mode")
    if source_mode == "bluesky":
        return BlueskyClient(config).fetch()
    client = RedditClient(config)
    return client.fetch()
