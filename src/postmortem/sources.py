from __future__ import annotations

import argparse
from pathlib import Path

from reddit_automation.storage.db import Database
from reddit_automation.storage.source_queue import SourceQueueRepository
from reddit_automation.utils.paths import DB_PATH, SCHEMA_SQL_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="postmortem.sources")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue_parser = subparsers.add_parser("enqueue")
    enqueue_parser.add_argument("urls", nargs="+")
    _add_db_args(enqueue_parser)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--status", default="pending", choices=["pending", "failed"])
    list_parser.add_argument("--limit", type=int, default=50)
    _add_db_args(list_parser)

    args = parser.parse_args(argv)
    db = Database(Path(args.db_path))
    db.init_schema(args.schema_path)
    repo = SourceQueueRepository(db)

    if args.command == "enqueue":
        for url in args.urls:
            item = repo.enqueue_url(url)
            print(f"queued {item['source']} {item['source_url']} status={item['status']} id={item['id']}")
        return 0

    if args.command == "list":
        items = repo.retry_failed(args.limit) if args.status == "failed" else repo.pending(args.limit)
        for item in items:
            print(f"{item['id']} {item['status']} {item['source']} {item['source_url']}")
        return 0

    return 2


def _add_db_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db-path", default=str(DB_PATH))
    parser.add_argument("--schema-path", default=str(SCHEMA_SQL_PATH))


if __name__ == "__main__":
    raise SystemExit(main())
