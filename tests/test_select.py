from reddit_automation.pipeline.select import select_episode_items


def test_select_episode_items_returns_three_primaries_and_two_backups():
    config = {
        "project": {
            "final_pick_count": 3,
            "backup_pick_count": 2,
        }
    }
    scored_candidates = [
        {"reddit_post_id": "c1", "overall_score": 9.5, "keep": True},
        {"reddit_post_id": "c2", "overall_score": 9.0, "keep": True},
        {"reddit_post_id": "c3", "overall_score": 8.5, "keep": True},
        {"reddit_post_id": "c4", "overall_score": 8.0, "keep": True},
        {"reddit_post_id": "c5", "overall_score": 7.5, "keep": True},
    ]

    selection = select_episode_items(scored_candidates, config)

    assert selection == {
        "primary": [
            {"reddit_post_id": "c1", "overall_score": 9.5, "keep": True},
            {"reddit_post_id": "c2", "overall_score": 9.0, "keep": True},
            {"reddit_post_id": "c3", "overall_score": 8.5, "keep": True},
        ],
        "backups": [
            {"reddit_post_id": "c4", "overall_score": 8.0, "keep": True},
            {"reddit_post_id": "c5", "overall_score": 7.5, "keep": True},
        ],
    }


def test_select_episode_items_excludes_candidates_with_keep_false():
    config = {
        "project": {
            "final_pick_count": 3,
            "backup_pick_count": 2,
        }
    }
    scored_candidates = [
        {"reddit_post_id": "c1", "overall_score": 9.5, "keep": True},
        {"reddit_post_id": "c2", "overall_score": 9.0, "keep": False},
        {"reddit_post_id": "c3", "overall_score": 8.5, "keep": True},
        {"reddit_post_id": "c4", "overall_score": 8.0, "keep": True},
        {"reddit_post_id": "c5", "overall_score": 7.5, "keep": True},
        {"reddit_post_id": "c6", "overall_score": 7.0, "keep": True},
    ]

    selection = select_episode_items(scored_candidates, config)

    assert selection == {
        "primary": [
            {"reddit_post_id": "c1", "overall_score": 9.5, "keep": True},
            {"reddit_post_id": "c3", "overall_score": 8.5, "keep": True},
            {"reddit_post_id": "c4", "overall_score": 8.0, "keep": True},
        ],
        "backups": [
            {"reddit_post_id": "c5", "overall_score": 7.5, "keep": True},
            {"reddit_post_id": "c6", "overall_score": 7.0, "keep": True},
        ],
    }


def test_select_episode_items_preserves_incoming_score_order():
    config = {
        "project": {
            "final_pick_count": 3,
            "backup_pick_count": 2,
        }
    }
    scored_candidates = [
        {"reddit_post_id": "highest", "overall_score": 9.9, "keep": True},
        {"reddit_post_id": "dropped", "overall_score": 9.8, "keep": False},
        {"reddit_post_id": "next", "overall_score": 9.1, "keep": True},
        {"reddit_post_id": "third", "overall_score": 8.7, "keep": True},
        {"reddit_post_id": "backup1", "overall_score": 8.0, "keep": True},
        {"reddit_post_id": "backup2", "overall_score": 7.6, "keep": True},
    ]

    selection = select_episode_items(scored_candidates, config)

    assert [candidate["reddit_post_id"] for candidate in selection["primary"]] == [
        "highest",
        "next",
        "third",
    ]
    assert [candidate["reddit_post_id"] for candidate in selection["backups"]] == [
        "backup1",
        "backup2",
    ]
