from __future__ import annotations

import sqlite3
from pathlib import Path

from reddit_automation.utils.paths import DB_PATH, SCHEMA_SQL_PATH


class Database:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self, schema_path: str | Path = SCHEMA_SQL_PATH) -> None:
        schema_file = Path(schema_path)
        sql = schema_file.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(sql)
            conn.commit()
