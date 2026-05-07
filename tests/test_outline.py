from reddit_automation.pipeline.outline import build_episode_outline


def test_build_episode_outline_returns_primary_items_as_ordered_segments():
    selected_items = {
        "primary": [
            {"candidate_id": "p1", "title": "First story", "source_community": "AskReddit"},
            {"candidate_id": "p2", "title": "Second story", "source_community": "tifu"},
            {"candidate_id": "p3", "title": "Third story", "source_community": "AmItheAsshole"},
        ],
        "backups": [
            {"candidate_id": "b1", "title": "Backup story", "source_community": "AskReddit"}
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
        {"candidate_id": "p1", "title": "First story", "source_community": "AskReddit"},
        {"candidate_id": "p2", "title": "Second story", "source_community": "tifu"},
        {"candidate_id": "p3", "title": "Third story", "source_community": "AmItheAsshole"},
    ]



def test_build_episode_outline_uses_episode_target_minutes_as_segment_budget():
    selected_items = {
        "primary": [
            {"candidate_id": "p1", "title": "First story", "source_community": "AskReddit"},
            {"candidate_id": "p2", "title": "Second story", "source_community": "tifu"},
            {"candidate_id": "p3", "title": "Third story", "source_community": "AmItheAsshole"},
        ],
        "backups": [],
    }
    config = {
        "project": {"episode_target_minutes": 2},
        "scripting": {"target_segments": 3, "minutes_per_segment": 1.5},
    }

    outline = build_episode_outline(selected_items, config)

    assert [segment["source"]["candidate_id"] for segment in outline["segments"]] == ["p1"]



def test_build_episode_outline_adds_segment_visual_notes_from_story_context():
    selected_items = {
        "primary": [
            {
                "candidate_id": "p1",
                "title": "First story",
                "source_community": "AskReddit",
                "summary": "A lunch prank blew up the office.",
            },
        ],
        "backups": [],
    }
    config = {
        "scripting": {
            "target_segments": 1,
        }
    }

    outline = build_episode_outline(selected_items, config)

    visual_note = outline["segments"][0]["visual_notes"][0]
    assert "Placeholder" not in visual_note
    assert "r/AskReddit" in visual_note
    assert "A lunch prank blew up the office." in visual_note


def test_build_episode_outline_returns_selection_primary_items_in_order():
    selected_items = {
        "primary": [
            {
                "candidate_id": "c1",
                "title": "First story",
                "author": "user1",
                "url": "https://reddit.com/1",
                "overall_score": 9.5,
            },
            {
                "candidate_id": "c2",
                "title": "Second story",
                "author": "user2",
                "url": "https://reddit.com/2",
                "overall_score": 9.0,
            },
        ],
        "backups": [
            {
                "candidate_id": "b1",
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
                "candidate_id": "c1",
                "source": "reddit",
                "source_id": "c1",
                "source_community": None,
                "title": "First story",
                "author": "user1",
                "url": "https://reddit.com/1",
            },
            {
                "position": 2,
                "candidate_id": "c2",
                "source": "reddit",
                "source_id": "c2",
                "source_community": None,
                "title": "Second story",
                "author": "user2",
                "url": "https://reddit.com/2",
            },
        ]
    }


def test_build_episode_outline_adds_title_angle_and_cold_open_from_selected_story():
    selected_items = {
        "primary": [
            {
                "candidate_id": "abc123",
                "source_community": "AmItheAsshole",
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
    assert "Placeholder" not in outline["title_angle"]
    assert "birthday dinner" in outline["title_angle"].lower()
    assert outline["cold_open"]["hook"]
    assert "Placeholder" not in outline["cold_open"]["hook"]
    assert "walked out" in outline["cold_open"]["hook"].lower()
    assert "r/AmItheAsshole" in outline["cold_open"]["visual_note"]
    assert "OP walked out after family drama." in outline["cold_open"]["visual_note"]



def test_build_episode_outline_adds_outro_from_primary_and_backup_story():
    selected_items = {
        "primary": [
            {
                "candidate_id": "abc123",
                "source_community": "AmItheAsshole",
                "title": "AITA for leaving my own birthday dinner?",
                "summary": "OP walked out after family drama.",
                "author": "user1",
                "url": "https://reddit.com/abc123",
            }
        ],
        "backups": [
            {
                "candidate_id": "backup456",
                "source_community": "tifu",
                "title": "TIFU by sending a complaint to the wrong email.",
                "summary": "A workplace complaint landed in the boss inbox.",
                "author": "user2",
                "url": "https://reddit.com/backup456",
            }
        ],
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

    assert outline["outro"]["callback"]
    assert "Placeholder" not in outline["outro"]["callback"]
    assert "birthday dinner" in outline["outro"]["callback"].lower()
    assert outline["outro"]["tomorrow_tease"]
    assert "Placeholder" not in outline["outro"]["tomorrow_tease"]
    assert "wrong email" in outline["outro"]["tomorrow_tease"].lower()
    assert "Placeholder" not in outline["outro"]["visual_note"]
    assert "r/AmItheAsshole" in outline["outro"]["visual_note"]
