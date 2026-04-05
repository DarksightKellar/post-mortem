from reddit_automation.pipeline.visuals import build_visual_plan


def test_build_visual_plan_returns_title_card_scene_from_outline_title_and_episode_date():
    outline = {
        "episode_date": "2026-04-03",
        "title_angle": "Placeholder: Funniest threads today",
    }

    visual_plan = build_visual_plan(outline, {})

    assert visual_plan == {
        "episode_date": "2026-04-03",
        "title": "Placeholder: Funniest threads today",
        "scenes": [
            {"type": "title_card", "text": "Placeholder: Funniest threads today"}
        ],
    }


def test_build_visual_plan_appends_cold_open_scene_from_outline_visual_note():
    outline = {
        "episode_date": "2026-04-03",
        "title_angle": "Placeholder: Funniest threads today",
        "cold_open": {"visual_note": "Two hosts at the desk."},
    }

    visual_plan = build_visual_plan(outline, {})

    assert visual_plan["scenes"] == [
        {"type": "title_card", "text": "Placeholder: Funniest threads today"},
        {"type": "cold_open", "text": "Two hosts at the desk."},
    ]


def test_build_visual_plan_appends_outro_scene_from_outline_visual_note():
    outline = {
        "episode_date": "2026-04-03",
        "title_angle": "Placeholder: Funniest threads today",
        "outro": {"visual_note": "Show logo and tomorrow teaser card."},
    }

    visual_plan = build_visual_plan(outline, {})

    assert visual_plan["scenes"] == [
        {"type": "title_card", "text": "Placeholder: Funniest threads today"},
        {"type": "outro", "text": "Show logo and tomorrow teaser card."},
    ]


def test_build_visual_plan_appends_first_segment_scene_from_segment_visual_notes():
    outline = {
        "episode_date": "2026-04-03",
        "title_angle": "Placeholder: Funniest threads today",
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                },
                "visual_notes": ["Placeholder visual note for p1"],
            }
        ],
    }

    visual_plan = build_visual_plan(outline, {})

    assert visual_plan["scenes"] == [
        {"type": "title_card", "text": "Placeholder: Funniest threads today"},
        {"type": "segment", "position": 1, "text": "Placeholder visual note for p1"},
    ]


def test_build_visual_plan_returns_full_scene_sequence_with_all_segment_scenes_in_order():
    outline = {
        "episode_date": "2026-04-03",
        "title_angle": "Placeholder: Funniest threads today",
        "cold_open": {"visual_note": "Two hosts at the desk."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                },
                "visual_notes": ["Placeholder visual note for p1"],
            },
            {
                "position": 2,
                "source": {
                    "reddit_post_id": "p2",
                    "title": "Second story",
                    "subreddit": "AskReddit",
                },
                "visual_notes": ["Placeholder visual note for p2"],
            },
        ],
        "outro": {"visual_note": "Show logo and tomorrow teaser card."},
    }

    visual_plan = build_visual_plan(outline, {})

    assert visual_plan["scenes"] == [
        {"type": "title_card", "text": "Placeholder: Funniest threads today"},
        {"type": "cold_open", "text": "Two hosts at the desk."},
        {"type": "segment", "position": 1, "text": "Placeholder visual note for p1"},
        {"type": "segment", "position": 2, "text": "Placeholder visual note for p2"},
        {"type": "outro", "text": "Show logo and tomorrow teaser card."},
    ]
