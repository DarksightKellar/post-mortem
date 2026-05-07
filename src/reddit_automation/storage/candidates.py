from __future__ import annotations

import json

from reddit_automation.storage.db import Database


def _default_source_id(candidate: dict) -> str:
    candidate_id = str(candidate["candidate_id"])
    source = str(candidate.get("source") or "reddit")
    prefix = f"{source}:"
    if candidate_id.startswith(prefix):
        return candidate_id[len(prefix) :]
    return candidate_id


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
                INSERT INTO source_candidates (
                    candidate_id,
                    source,
                    source_id,
                    source_community,
                    title,
                    body,
                    url,
                    author,
                    created_utc,
                    score,
                    comment_count,
                    raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    source = excluded.source,
                    source_id = excluded.source_id,
                    source_community = excluded.source_community,
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
                        row["candidate_id"],
                        row.get("source") or "reddit",
                        row.get("source_id") or _default_source_id(row),
                        row["source_community"],
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

    def replace_comments(self, candidate_id: str, comments: list[dict]) -> int:
        rows = list(comments)

        with self.db.connect() as conn:
            conn.execute(
                "DELETE FROM candidate_comments WHERE candidate_id = ?",
                (candidate_id,),
            )
            conn.executemany(
                """
                INSERT INTO candidate_comments (
                    candidate_id,
                    comment_id,
                    body,
                    score,
                    author,
                    created_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        candidate_id,
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
