from __future__ import annotations

import json

from reddit_automation.storage.db import Database


class RunLogRepository:
    def __init__(self, db: Database):
        self.db = db

    def log(self, run_date: str, stage: str, status: str, message: str, payload: dict | None = None) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO run_logs (run_date, stage, status, message, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_date, stage, status, message, json.dumps(payload or {})),
            )
            conn.commit()
