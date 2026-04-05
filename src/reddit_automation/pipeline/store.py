from __future__ import annotations

from reddit_automation.storage.candidates import CandidateRepository
from reddit_automation.storage.db import Database


def store_candidates(candidates: list[dict], db: Database) -> dict:
    repo = CandidateRepository(db)
    stored_count = repo.upsert_candidates(candidates)
    comment_count = 0

    for candidate in candidates:
        comment_count += repo.replace_comments(
            candidate["reddit_post_id"],
            candidate.get("top_comments", []),
        )

    return {"stored_candidates": stored_count, "stored_comments": comment_count}
