"""Integration test proving that build_episode_outline output is compatible with build_visual_plan.

This is a 'thin-slice' test: it calls the real outline.py and real visuals.py
without any mocking or monkeypatching, proving the end-to-end contract between them.
"""

from reddit_automation.pipeline.outline import build_episode_outline
from reddit_automation.pipeline.visuals import build_visual_plan


def _make_minimal_selected_candidates():
    return {
        "primary": [
            {
                "reddit_post_id": "post_1",
                "title": "AITA for leaving my own birthday dinner?",
                "subreddit": "AmItheAsshole",
            },
            {
                "reddit_post_id": "post_2",
                "title": "TIFU by sending a complaint to the wrong email.",
                "subreddit": "tifu",
            },
        ],
        "backups": [],
    }


def _make_config_with_date(target_segments=2):
    return {
        "project": {
            "episode_date": "2026-04-03",
        },
        "scripting": {
            "target_segments": target_segments,
        },
    }


def test_outline_to_visuals_integration():
    """Pass the real build_episode_outline result into build_visual_plan.
    Assert the visual plan has 'scenes' list and 'episode_date' string."""
    selected_candidates = _make_minimal_selected_candidates()
    config = _make_config_with_date(target_segments=2)

    # Call the real build_episode_outline
    outline = build_episode_outline(selected_candidates, config)

    # Pass the real outline into the real build_visual_plan
    # Assert: no exception raised (contract compatibility)
    visual_plan = build_visual_plan(outline, config)

    # Assert: visual plan has scenes list
    assert isinstance(visual_plan["scenes"], list)

    # Assert: visual plan has episode_date
    assert isinstance(visual_plan["episode_date"], str)
    assert visual_plan["episode_date"] == "2026-04-03"

    # Assert: scenes include a title_card
    assert any(s["type"] == "title_card" for s in visual_plan["scenes"])

    # Assert: scenes include segment entries for each outline segment
    segment_scenes = [s for s in visual_plan["scenes"] if s["type"] == "segment"]
    assert len(segment_scenes) == config["scripting"]["target_segments"]
