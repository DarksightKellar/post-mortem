from __future__ import annotations

from reddit_automation.storage.db import Database


SCHEMA_PATH = "data/schema.sql"


def test_postmortem_sources_enqueue_adds_url_to_queue(tmp_path, capsys):
    from postmortem import sources

    db_path = tmp_path / "sources.db"
    result = sources.main(
        [
            "enqueue",
            "https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i",
            "--db-path",
            str(db_path),
            "--schema-path",
            SCHEMA_PATH,
        ]
    )

    assert result == 0
    assert "queued bluesky" in capsys.readouterr().out
    db = Database(db_path)
    with db.connect() as conn:
        row = conn.execute("SELECT source, source_url, status FROM source_queue").fetchone()
    assert dict(row) == {
        "source": "bluesky",
        "source_url": "https://bsky.app/profile/bsky.app/post/3lqv2pprabs2i",
        "status": "pending",
    }


def test_postmortem_sources_list_prints_queue_items(tmp_path, capsys):
    from postmortem import sources

    db_path = tmp_path / "sources.db"
    sources.main(
        [
            "enqueue",
            "https://www.reddit.com/r/tifu/comments/abc123/title/",
            "--db-path",
            str(db_path),
            "--schema-path",
            SCHEMA_PATH,
        ]
    )
    capsys.readouterr()

    result = sources.main(["list", "--db-path", str(db_path), "--schema-path", SCHEMA_PATH])

    output = capsys.readouterr().out
    assert result == 0
    assert "pending reddit https://www.reddit.com/r/tifu/comments/abc123/title/" in output
