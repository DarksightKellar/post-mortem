import sqlite3

from reddit_automation.storage.bootstrap import bootstrap_database


def test_bootstrap_database_initializes_configured_database_with_schema(tmp_path):
    db_path = tmp_path / "test.db"
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        "CREATE TABLE sample_table (id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )
    config = {
        "storage": {
            "db_path": str(db_path),
            "schema_path": str(schema_path),
        }
    }

    db = bootstrap_database(config)

    assert db.db_path == db_path
    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sample_table'"
        ).fetchone()

    assert row == ("sample_table",)
