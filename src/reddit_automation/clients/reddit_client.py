from __future__ import annotations

from typing import Any


class RedditClient:
    def __init__(self, config: dict):
        self.config = config

    def normalize_submission(self, submission: dict[str, Any], top_n_comments: int) -> dict[str, Any]:
        return {
            "reddit_post_id": submission["id"],
            "subreddit": submission["subreddit"],
            "title": submission["title"],
            "body": submission.get("selftext", ""),
            "url": submission["url"],
            "author": submission.get("author"),
            "created_utc": submission["created_utc"],
            "score": submission.get("score", 0),
            "comment_count": submission.get("num_comments", 0),
            "raw_json": {"id": submission["id"]},
            "top_comments": [
                {
                    "comment_id": comment["id"],
                    "body": comment["body"],
                    "score": comment.get("score", 0),
                    "author": comment.get("author"),
                    "created_utc": comment.get("created_utc"),
                }
                for comment in submission.get("comments", [])[:top_n_comments]
            ],
        }

    def fetch(self) -> list[dict[str, Any]]:
        top_n_comments = self.config.get("comments", {}).get("top_n_per_candidate", 5)
        submissions = self.config.get("reddit_test_data", {}).get("submissions", [])
        return [
            self.normalize_submission(submission, top_n_comments=top_n_comments)
            for submission in submissions
        ]
