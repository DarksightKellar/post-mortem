from __future__ import annotations

import json

from reddit_automation.storage.db import Database


class CandidateRepository:
    def __init__(self, db: Database):
        self.db = db

    def upsert_candidates(self, candidates: list[dict]) -> int:
        rows = list(candidates)
        if not rows:
            return 0

        with self.db.connect() as conn:
            conn.executemany(
                """
                INSERT INTO reddit_candidates (
                    reddit_post_id,
                    subreddit,
                    title,
                    body,
                    url,
                    author,
                    created_utc,
                    score,
                    comment_count,
                    raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(reddit_post_id) DO UPDATE SET
                    subreddit = excluded.subreddit,
                    title = excluded.title,
                    body = excluded.body,
                    url = excluded.url,
                    author = excluded.author,
                    created_utc = excluded.created_utc,
                    score = excluded.score,
                    comment_count = excluded.comment_count,
                    raw_json = excluded.raw_json,
                    fetched_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        row["reddit_post_id"],
                        row["subreddit"],
                        row["title"],
                        row.get("body", ""),
                        row["url"],
                        row.get("author"),
                        row["created_utc"],
                        row.get("score", 0),
                        row.get("comment_count", 0),
                        json.dumps(row.get("raw_json", {})),
                    )
                    for row in rows
                ],
            )
            conn.commit()

        return len(rows)

    def replace_comments(self, reddit_post_id: str, comments: list[dict]) -> int:
        rows = list(comments)

        with self.db.connect() as conn:
            conn.execute(
                "DELETE FROM candidate_comments WHERE reddit_post_id = ?",
                (reddit_post_id,),
            )
            conn.executemany(
                """
                INSERT INTO candidate_comments (
                    reddit_post_id,
                    comment_id,
                    body,
                    score,
                    author,
                    created_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        reddit_post_id,
                        row["comment_id"],
                        row["body"],
                        row.get("score", 0),
                        row.get("author"),
                        row.get("created_utc"),
                    )
                    for row in rows
                ],
            )
            conn.commit()

        return len(rows)
