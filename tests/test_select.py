from reddit_automation.pipeline.select import select_episode_items


def test_select_episode_items_returns_three_primaries_and_two_backups():
    config = {
        "project": {
            "final_pick_count": 3,
            "backup_pick_count": 2,
        }
    }
    scored_candidates = [
        {"candidate_id": "c1", "overall_score": 9.5, "keep": True},
        {"candidate_id": "c2", "overall_score": 9.0, "keep": True},
        {"candidate_id": "c3", "overall_score": 8.5, "keep": True},
        {"candidate_id": "c4", "overall_score": 8.0, "keep": True},
        {"candidate_id": "c5", "overall_score": 7.5, "keep": True},
    ]

    selection = select_episode_items(scored_candidates, config)

    assert selection == {
        "primary": [
            {"candidate_id": "c1", "overall_score": 9.5, "keep": True},
            {"candidate_id": "c2", "overall_score": 9.0, "keep": True},
            {"candidate_id": "c3", "overall_score": 8.5, "keep": True},
        ],
        "backups": [
            {"candidate_id": "c4", "overall_score": 8.0, "keep": True},
            {"candidate_id": "c5", "overall_score": 7.5, "keep": True},
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
        {"candidate_id": "c1", "overall_score": 9.5, "keep": True},
        {"candidate_id": "c2", "overall_score": 9.0, "keep": False},
        {"candidate_id": "c3", "overall_score": 8.5, "keep": True},
        {"candidate_id": "c4", "overall_score": 8.0, "keep": True},
        {"candidate_id": "c5", "overall_score": 7.5, "keep": True},
        {"candidate_id": "c6", "overall_score": 7.0, "keep": True},
    ]

    selection = select_episode_items(scored_candidates, config)

    assert selection == {
        "primary": [
            {"candidate_id": "c1", "overall_score": 9.5, "keep": True},
            {"candidate_id": "c3", "overall_score": 8.5, "keep": True},
            {"candidate_id": "c4", "overall_score": 8.0, "keep": True},
        ],
        "backups": [
            {"candidate_id": "c5", "overall_score": 7.5, "keep": True},
            {"candidate_id": "c6", "overall_score": 7.0, "keep": True},
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
        {"candidate_id": "highest", "overall_score": 9.9, "keep": True},
        {"candidate_id": "dropped", "overall_score": 9.8, "keep": False},
        {"candidate_id": "next", "overall_score": 9.1, "keep": True},
        {"candidate_id": "third", "overall_score": 8.7, "keep": True},
        {"candidate_id": "backup1", "overall_score": 8.0, "keep": True},
        {"candidate_id": "backup2", "overall_score": 7.6, "keep": True},
    ]

    selection = select_episode_items(scored_candidates, config)

    assert [candidate["candidate_id"] for candidate in selection["primary"]] == [
        "highest",
        "next",
        "third",
    ]
    assert [candidate["candidate_id"] for candidate in selection["backups"]] == [
        "backup1",
        "backup2",
    ]
