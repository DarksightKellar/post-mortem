from __future__ import annotations

from pathlib import Path

from reddit_automation.storage.db import Database
from reddit_automation.utils.config import load_config
from reddit_automation.utils.logging import get_logger
from reddit_automation.utils.paths import DB_PATH, SCHEMA_SQL_PATH

logger = get_logger(__name__)


def bootstrap_database(config: dict | None = None) -> Database:
    resolved_config = config or load_config()
    storage_config = resolved_config.get("storage", {})

    db_path = storage_config.get("db_path") or DB_PATH
    schema_path = storage_config.get("schema_path") or SCHEMA_SQL_PATH

    db = Database(db_path)
    db.init_schema(schema_path)
    logger.info("Database schema initialized")
    return db
