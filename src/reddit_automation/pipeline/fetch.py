from __future__ import annotations

from reddit_automation.clients.reddit_client import RedditClient


def fetch_candidates(config: dict) -> list[dict]:
    client = RedditClient(config)
    return client.fetch()
