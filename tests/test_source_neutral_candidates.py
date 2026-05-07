import json
import sqlite3

from reddit_automation.clients.reddit_client import RedditClient
from reddit_automation.storage.bootstrap import bootstrap_database
from reddit_automation.storage.candidates import CandidateRepository


def _source_neutral_schema() -> str:
    return """
    CREATE TABLE source_candidates (
        candidate_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        source_id TEXT NOT NULL,
        source_community TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL,
        author TEXT,
        created_utc INTEGER NOT NULL,
        score INTEGER NOT NULL DEFAULT 0,
        comment_count INTEGER NOT NULL DEFAULT 0,
        raw_json TEXT,
        fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id)
    );
    CREATE TABLE candidate_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT NOT NULL,
        comment_id TEXT NOT NULL UNIQUE,
        body TEXT NOT NULL,
        score INTEGER NOT NULL DEFAULT 0,
        author TEXT,
        created_utc INTEGER,
        FOREIGN KEY (candidate_id) REFERENCES source_candidates(candidate_id) ON DELETE CASCADE
    );
    """


def test_reddit_normalization_uses_source_neutral_candidate_fields():
    client = RedditClient(config={})

    candidate = client.normalize_submission(
        {
            "id": "abc123",
            "subreddit": "AskReddit",
            "title": "What happened at work?",
            "selftext": "Someone microwaved fish.",
            "url": "https://reddit.com/r/AskReddit/comments/abc123",
            "author": "kelvin",
            "created_utc": 1712345678,
            "score": 420,
            "num_comments": 2,
            "comments": [],
        },
        top_n_comments=2,
    )

    assert candidate["candidate_id"] == "reddit:abc123"
    assert candidate["source"] == "reddit"
    assert candidate["source_id"] == "abc123"
    assert candidate["source_community"] == "AskReddit"
    assert "reddit_post_id" not in candidate
    assert "subreddit" not in candidate


def test_repository_persists_source_neutral_candidate_and_comments(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(_source_neutral_schema(), encoding="utf-8")
    db = bootstrap_database({"storage": {"db_path": str(db_path), "schema_path": str(schema_path)}})
    repo = CandidateRepository(db)
    candidate = {
        "candidate_id": "bluesky:at://did:plc:alice/app.bsky.feed.post/3kabc",
        "source": "bluesky",
        "source_id": "at://did:plc:alice/app.bsky.feed.post/3kabc",
        "source_community": "alice.example",
        "title": "Office fridge evidence",
        "body": "I labeled the office fridge shelf evidence.",
        "url": "https://bsky.app/profile/alice.example/post/3kabc",
        "author": "alice.example",
        "created_utc": 1778157000,
        "score": 20,
        "comment_count": 1,
        "raw_json": {"source": "bluesky"},
        "top_comments": [
            {
                "comment_id": "at://did:plc:bob/app.bsky.feed.post/3kdef",
                "body": "That is how every office gets a fridge policy.",
                "score": 44,
                "author": "bob.example",
                "created_utc": 1778157060,
            }
        ],
    }

    assert repo.upsert_candidates([candidate]) == 1
    assert repo.replace_comments(candidate["candidate_id"], candidate["top_comments"]) == 1

    with sqlite3.connect(db_path) as conn:
        candidate_row = conn.execute(
            """
            SELECT candidate_id, source, source_id, source_community, title, raw_json
            FROM source_candidates
            WHERE candidate_id = ?
            """,
            (candidate["candidate_id"],),
        ).fetchone()
        comment_row = conn.execute(
            """
            SELECT candidate_id, comment_id, body, score, author, created_utc
            FROM candidate_comments
            WHERE candidate_id = ?
            """,
            (candidate["candidate_id"],),
        ).fetchone()

    assert candidate_row == (
        "bluesky:at://did:plc:alice/app.bsky.feed.post/3kabc",
        "bluesky",
        "at://did:plc:alice/app.bsky.feed.post/3kabc",
        "alice.example",
        "Office fridge evidence",
        json.dumps({"source": "bluesky"}),
    )
    assert comment_row == (
        "bluesky:at://did:plc:alice/app.bsky.feed.post/3kabc",
        "at://did:plc:bob/app.bsky.feed.post/3kdef",
        "That is how every office gets a fridge policy.",
        44,
        "bob.example",
        1778157060,
    )
