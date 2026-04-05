from reddit_automation.pipeline.script import write_episode_script


def test_write_episode_script_returns_title_from_outline_title_angle():
    outline = {
        "title_angle": "Placeholder: AITA for leaving my own birthday dinner?",
    }
    config = {}

    episode_script = write_episode_script(outline, config)

    assert episode_script["title"] == "Placeholder: AITA for leaving my own birthday dinner?"



def test_write_episode_script_returns_segment_skeletons_from_outline_segments():
    outline = {
        "title_angle": "Placeholder: Funniest threads today",
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                },
            },
            {
                "position": 2,
                "source": {
                    "reddit_post_id": "p2",
                    "title": "Second story",
                    "subreddit": "tifu",
                },
            },
        ],
    }
    config = {}

    episode_script = write_episode_script(outline, config)

    assert [
        {
            "position": segment["position"],
            "reddit_post_id": segment["reddit_post_id"],
        }
        for segment in episode_script["segments"]
    ] == [
        {
            "position": 1,
            "reddit_post_id": "p1",
        },
        {
            "position": 2,
            "reddit_post_id": "p2",
        },
    ]



def test_write_episode_script_adds_alternating_host_lines_to_each_segment():
    outline = {
        "title_angle": "Placeholder: Funniest threads today",
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                },
            }
        ],
    }
    config = {
        "hosts": {
            "host_1": {"key": "host_1"},
            "host_2": {"key": "host_2"},
        }
    }

    episode_script = write_episode_script(outline, config)

    assert episode_script["segments"][0]["lines"] == [
        {
            "speaker": "host_1",
            "text": "Setup: First story",
        },
        {
            "speaker": "host_2",
            "text": "Reaction: First story",
        },
    ]



def test_write_episode_script_adds_cold_open_lines_from_outline_hook():
    outline = {
        "title_angle": "Placeholder: Funniest threads today",
        "cold_open": {
            "hook": "Today got absurd fast.",
            "visual_note": "Two hosts at the desk.",
        },
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                },
            }
        ],
    }
    config = {
        "hosts": {
            "host_1": {"key": "host_1"},
            "host_2": {"key": "host_2"},
        }
    }

    episode_script = write_episode_script(outline, config)

    assert episode_script["cold_open"]["lines"] == [
        {
            "speaker": "host_1",
            "text": "Cold open: Today got absurd fast.",
        },
        {
            "speaker": "host_2",
            "text": "Cold open reaction: Today got absurd fast.",
        },
    ]



def test_write_episode_script_copies_source_title_and_subreddit_to_each_segment():
    outline = {
        "title_angle": "Placeholder: Funniest threads today",
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                },
            },
            {
                "position": 2,
                "source": {
                    "reddit_post_id": "p2",
                    "title": "Second story",
                    "subreddit": "tifu",
                },
            },
        ],
    }
    config = {}

    episode_script = write_episode_script(outline, config)

    assert [
        {
            "position": segment["position"],
            "reddit_post_id": segment["reddit_post_id"],
            "source_title": segment["source_title"],
            "subreddit": segment["subreddit"],
        }
        for segment in episode_script["segments"]
    ] == [
        {
            "position": 1,
            "reddit_post_id": "p1",
            "source_title": "First story",
            "subreddit": "AskReddit",
        },
        {
            "position": 2,
            "reddit_post_id": "p2",
            "source_title": "Second story",
            "subreddit": "tifu",
        },
    ]



def test_write_episode_script_adds_outro_placeholder_lines_from_outline_outro():
    outline = {
        "title_angle": "Placeholder: Funniest threads today",
        "outro": {
            "callback": "Remember the birthday dinner meltdown.",
            "tomorrow_tease": "Tomorrow we get into the pettiest roommate fights.",
            "visual_note": "Placeholder outro visual",
        },
    }
    config = {
        "hosts": {
            "host_1": {"key": "host_1"},
            "host_2": {"key": "host_2"},
        }
    }

    episode_script = write_episode_script(outline, config)

    assert episode_script["outro"]["lines"] == [
        {
            "speaker": "host_1",
            "text": "Callback: Remember the birthday dinner meltdown.",
        },
        {
            "speaker": "host_2",
            "text": "Tease: Tomorrow we get into the pettiest roommate fights.",
        },
    ]
