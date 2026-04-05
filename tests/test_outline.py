from reddit_automation.pipeline.outline import build_episode_outline


def test_build_episode_outline_returns_primary_items_as_ordered_segments():
    selected_items = {
        "primary": [
            {"reddit_post_id": "p1", "title": "First story", "subreddit": "AskReddit"},
            {"reddit_post_id": "p2", "title": "Second story", "subreddit": "tifu"},
            {"reddit_post_id": "p3", "title": "Third story", "subreddit": "AmItheAsshole"},
        ],
        "backups": [
            {"reddit_post_id": "b1", "title": "Backup story", "subreddit": "AskReddit"}
        ],
    }
    config = {
        "scripting": {
            "target_segments": 3,
        }
    }

    outline = build_episode_outline(selected_items, config)

    assert [segment["position"] for segment in outline["segments"]] == [1, 2, 3]
    assert [segment["source"] for segment in outline["segments"]] == [
        {"reddit_post_id": "p1", "title": "First story", "subreddit": "AskReddit"},
        {"reddit_post_id": "p2", "title": "Second story", "subreddit": "tifu"},
        {"reddit_post_id": "p3", "title": "Third story", "subreddit": "AmItheAsshole"},
    ]



def test_build_episode_outline_adds_segment_visual_notes_placeholders():
    selected_items = {
        "primary": [
            {"reddit_post_id": "p1", "title": "First story", "subreddit": "AskReddit"},
        ],
        "backups": [],
    }
    config = {
        "scripting": {
            "target_segments": 1,
        }
    }

    outline = build_episode_outline(selected_items, config)

    assert outline["segments"][0]["visual_notes"] == ["Placeholder visual note for p1"]


def test_build_episode_outline_returns_selection_primary_items_in_order():
    selected_items = {
        "primary": [
            {
                "reddit_post_id": "c1",
                "title": "First story",
                "author": "user1",
                "url": "https://reddit.com/1",
                "overall_score": 9.5,
            },
            {
                "reddit_post_id": "c2",
                "title": "Second story",
                "author": "user2",
                "url": "https://reddit.com/2",
                "overall_score": 9.0,
            },
        ],
        "backups": [
            {
                "reddit_post_id": "b1",
                "title": "Backup story",
                "author": "user3",
                "url": "https://reddit.com/3",
                "overall_score": 8.0,
            }
        ],
    }
    config = {
        "scripting": {
            "target_segments": 2,
        }
    }

    outline = build_episode_outline(selected_items, config)

    assert outline["selection"] == {
        "primary_items": [
            {
                "position": 1,
                "reddit_post_id": "c1",
                "title": "First story",
                "author": "user1",
                "url": "https://reddit.com/1",
            },
            {
                "position": 2,
                "reddit_post_id": "c2",
                "title": "Second story",
                "author": "user2",
                "url": "https://reddit.com/2",
            },
        ]
    }


def test_build_episode_outline_adds_title_angle_and_cold_open_placeholders():
    selected_items = {
        "primary": [
            {
                "reddit_post_id": "abc123",
                "subreddit": "AmItheAsshole",
                "title": "AITA for leaving my own birthday dinner?",
                "summary": "OP walked out after family drama.",
                "author": "user1",
                "url": "https://reddit.com/abc123",
            }
        ],
        "backups": [],
    }
    config = {
        "project": {
            "episode_date": "2026-04-03",
        },
        "scripting": {
            "target_segments": 1,
        },
    }

    outline = build_episode_outline(selected_items, config)

    assert outline["episode_date"] == "2026-04-03"
    assert outline["title_angle"] == "Placeholder: AITA for leaving my own birthday dinner?"
    assert outline["cold_open"] == {
        "hook": "Placeholder hook for abc123",
        "visual_note": "Placeholder visual note for abc123",
    }



def test_build_episode_outline_adds_outro_placeholders():
    selected_items = {
        "primary": [
            {
                "reddit_post_id": "abc123",
                "subreddit": "AmItheAsshole",
                "title": "AITA for leaving my own birthday dinner?",
                "summary": "OP walked out after family drama.",
                "author": "user1",
                "url": "https://reddit.com/abc123",
            }
        ],
        "backups": [],
    }
    config = {
        "project": {
            "episode_date": "2026-04-03",
        },
        "scripting": {
            "target_segments": 1,
        },
    }

    outline = build_episode_outline(selected_items, config)

    assert outline["outro"] == {
        "callback": "Placeholder callback for abc123",
        "tomorrow_tease": "Placeholder tease for next episode",
        "visual_note": "Placeholder outro visual note for abc123",
    }
