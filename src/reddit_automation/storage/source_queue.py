from __future__ import annotations

from urllib.parse import urlparse

from reddit_automation.storage.db import Database


SUPPORTED_QUEUE_SOURCES = ("reddit", "bluesky")


def _row_to_dict(row) -> dict:
    return dict(row) if row is not None else {}


def _source_for_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host in {"reddit.com", "www.reddit.com", "old.reddit.com"}:
        return "reddit"
    if host == "bsky.app":
        return "bluesky"
    raise ValueError(f"Unsupported source URL: {url}")


class SourceQueueRepository:
    def __init__(self, db: Database):
        self.db = db

    def enqueue_url(self, url: str) -> dict:
        source = _source_for_url(url)
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO source_queue (source, source_url)
                VALUES (?, ?)
                ON CONFLICT(source, source_url) DO NOTHING
                """,
                (source, url),
            )
            row = conn.execute(
                """
                SELECT * FROM source_queue
                WHERE source = ? AND source_url = ?
                """,
                (source, url),
            ).fetchone()
            conn.commit()
        return _row_to_dict(row)

    def pending(self, limit: int) -> list[dict]:
        return self._items_by_status("pending", limit)

    def retry_failed(self, limit: int) -> list[dict]:
        return self._items_by_status("failed", limit)

    def claim_pending(self, limit: int) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM source_queue
                WHERE status = 'pending'
                ORDER BY created_at, id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"""
                    UPDATE source_queue
                    SET status = 'processing', updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                    """,
                    ids,
                )
            claimed = [self._get_by_id(conn, item_id) for item_id in ids]
            conn.commit()
        return [_row_to_dict(row) for row in claimed]

    def mark_done(self, item_id: int, candidate_id: str) -> dict:
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE source_queue
                SET status = 'done', candidate_id = ?, error_message = '', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (candidate_id, item_id),
            )
            row = self._get_by_id(conn, item_id)
            conn.commit()
        return _row_to_dict(row)

    def mark_failed(self, item_id: int, error_message: str) -> dict:
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE source_queue
                SET status = 'failed', error_message = ?, attempts = attempts + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (error_message, item_id),
            )
            row = self._get_by_id(conn, item_id)
            conn.commit()
        return _row_to_dict(row)

    def _items_by_status(self, status: str, limit: int) -> list[dict]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM source_queue
                WHERE status = ?
                ORDER BY created_at, id
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def _get_by_id(self, conn, item_id: int):
        return conn.execute(
            "SELECT * FROM source_queue WHERE id = ?",
            (item_id,),
        ).fetchone()
