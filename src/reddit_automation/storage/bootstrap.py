from __future__ import annotations

from pathlib import Path

from reddit_automation.storage.db import Database
from reddit_automation.utils.config import load_config
from reddit_automation.utils.logging import get_logger

logger = get_logger(__name__)


def bootstrap_database(config: dict | None = None) -> Database:
    resolved_config = config or load_config()
    storage_config = resolved_config.get("storage", {})

    db_path = storage_config.get("db_path")
    schema_path = storage_config.get("schema_path")

    db = Database(Path(db_path) if db_path else None)
    db.init_schema(Path(schema_path) if schema_path else None)
    logger.info("Database schema initialized")
    return db
