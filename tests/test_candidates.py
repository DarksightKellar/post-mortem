import sqlite3

from reddit_automation.storage.bootstrap import bootstrap_database
from reddit_automation.storage.candidates import CandidateRepository


def test_upsert_candidates_inserts_one_candidate_row(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        """
        CREATE TABLE reddit_candidates (
            reddit_post_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            author TEXT,
            created_utc INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            comment_count INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE candidate_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reddit_post_id TEXT NOT NULL,
            comment_id TEXT NOT NULL UNIQUE,
            body TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            author TEXT,
            created_utc INTEGER
        );
        """,
        encoding="utf-8",
    )
    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }
    candidate = {
        "reddit_post_id": "abc123",
        "subreddit": "AskReddit",
        "title": "Funniest thing that happened at work?",
        "body": "Someone microwaved fish and the office rioted.",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 420,
        "comment_count": 37,
        "raw_json": {"id": "abc123"},
    }

    db = bootstrap_database(config)
    repo = CandidateRepository(db)

    inserted_count = repo.upsert_candidates([candidate])

    assert inserted_count == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT reddit_post_id, subreddit, title, body, url, author, created_utc, score, comment_count, raw_json
            FROM reddit_candidates
            WHERE reddit_post_id = ?
            """,
            ("abc123",),
        ).fetchone()

    assert row == (
        "abc123",
        "AskReddit",
        "Funniest thing that happened at work?",
        "Someone microwaved fish and the office rioted.",
        "https://reddit.com/r/AskReddit/comments/abc123",
        "kelvin",
        1712345678,
        420,
        37,
        '{"id": "abc123"}',
    )


def test_replace_comments_inserts_comment_bundle_for_candidate(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        """
        CREATE TABLE reddit_candidates (
            reddit_post_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            author TEXT,
            created_utc INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            comment_count INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE candidate_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reddit_post_id TEXT NOT NULL,
            comment_id TEXT NOT NULL UNIQUE,
            body TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            author TEXT,
            created_utc INTEGER
        );
        """,
        encoding="utf-8",
    )
    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }
    candidate = {
        "reddit_post_id": "abc123",
        "subreddit": "AskReddit",
        "title": "Funniest thing that happened at work?",
        "body": "Someone microwaved fish and the office rioted.",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 420,
        "comment_count": 37,
        "raw_json": {"id": "abc123"},
    }
    comments = [
        {
            "comment_id": "c1",
            "body": "This office needed a hazmat team.",
            "score": 101,
            "author": "user1",
            "created_utc": 1712345680,
        },
        {
            "comment_id": "c2",
            "body": "Microwaved fish is a hostile work environment.",
            "score": 99,
            "author": "user2",
            "created_utc": 1712345685,
        },
    ]

    db = bootstrap_database(config)
    repo = CandidateRepository(db)
    repo.upsert_candidates([candidate])

    inserted_count = repo.replace_comments("abc123", comments)

    assert inserted_count == 2

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT reddit_post_id, comment_id, body, score, author, created_utc
            FROM candidate_comments
            WHERE reddit_post_id = ?
            ORDER BY comment_id
            """,
            ("abc123",),
        ).fetchall()

    assert rows == [
        (
            "abc123",
            "c1",
            "This office needed a hazmat team.",
            101,
            "user1",
            1712345680,
        ),
        (
            "abc123",
            "c2",
            "Microwaved fish is a hostile work environment.",
            99,
            "user2",
            1712345685,
        ),
    ]


def test_upsert_candidates_updates_existing_candidate_row(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        """
        CREATE TABLE reddit_candidates (
            reddit_post_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            author TEXT,
            created_utc INTEGER NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            comment_count INTEGER NOT NULL DEFAULT 0,
            raw_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE candidate_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reddit_post_id TEXT NOT NULL,
            comment_id TEXT NOT NULL UNIQUE,
            body TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            author TEXT,
            created_utc INTEGER
        );
        """,
        encoding="utf-8",
    )
    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }
    original_candidate = {
        "reddit_post_id": "abc123",
        "subreddit": "AskReddit",
        "title": "Original title",
        "body": "Original body",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin",
        "created_utc": 1712345678,
        "score": 100,
        "comment_count": 10,
        "raw_json": {"version": 1},
    }
    updated_candidate = {
        "reddit_post_id": "abc123",
        "subreddit": "AskReddit",
        "title": "Updated title",
        "body": "Updated body",
        "url": "https://reddit.com/r/AskReddit/comments/abc123",
        "author": "kelvin-2",
        "created_utc": 1712349999,
        "score": 250,
        "comment_count": 22,
        "raw_json": {"version": 2},
    }

    db = bootstrap_database(config)
    repo = CandidateRepository(db)
    repo.upsert_candidates([original_candidate])

    updated_count = repo.upsert_candidates([updated_candidate])

    assert updated_count == 1

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT reddit_post_id, subreddit, title, body, url, author, created_utc, score, comment_count, raw_json
            FROM reddit_candidates
            WHERE reddit_post_id = ?
            """,
            ("abc123",),
        ).fetchone()

    assert row == (
        "abc123",
        "AskReddit",
        "Updated title",
        "Updated body",
        "https://reddit.com/r/AskReddit/comments/abc123",
        "kelvin-2",
        1712349999,
        250,
        22,
        '{"version": 2}',
    )
