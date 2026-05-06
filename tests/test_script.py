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



def test_write_episode_script_adds_story_derived_host_lines_to_each_segment():
    outline = {
        "title_angle": "Messy Reddit stories",
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "First story",
                    "subreddit": "AskReddit",
                    "summary": "A lunch prank blew up the office.",
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

    lines = episode_script["segments"][0]["lines"]
    assert [line["speaker"] for line in lines] == ["host_1", "host_2"]
    assert lines[0]["text"] == "Over in r/AskReddit: A lunch prank blew up the office."
    assert lines[1]["text"] == 'The headline was: "First story".'


def test_write_episode_script_condenses_long_body_instead_of_reading_raw_post_twice():
    long_body = (
        "First I packed my lunch before work. "
        "Then TSA asked what was inside my bag. "
        "I said sandwich chips granola bars and C4 because that was the brand name of my preworkout. "
        "Police and K9 units showed up while I stood by the wall. "
        "After they realized it was a drink mix, everyone laughed and I became the new C4 guy."
    )
    outline = {
        "title_angle": "TSA lunchbox disaster",
        "cold_open": {
            "hook": long_body,
            "visual_note": "Airport security hallway.",
        },
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU by telling TSA I had C4 in my lunchbox",
                    "subreddit": "tifu",
                    "body": long_body,
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
    spoken_text = "\n".join(
        line["text"]
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    )

    assert long_body not in spoken_text
    assert "sandwich, chips, granola bars" in spoken_text
    assert "Police and K9 units show up" in spoken_text
    assert "The bad sentence:" not in spoken_text
    assert "Escalation:" not in spoken_text
    assert "Payoff:" not in spoken_text
    assert max(len(line["text"]) for line in episode_script["cold_open"]["lines"]) <= 180
    assert max(len(line["text"]) for line in episode_script["segments"][0]["lines"]) <= 260


def test_write_episode_script_skips_throwaway_leads_and_edit_notes_when_picking_beats():
    outline = {
        "title_angle": "TSA lunchbox disaster",
        "cold_open": {
            "hook": "Yikes! Useful hook follows.",
            "visual_note": "Airport security hallway.",
        },
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU by telling TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": (
                        "Yikes! "
                        "I packed a lunchbox with preworkout before my airport shift. "
                        "I told TSA it had sandwich chips granola bars and C4. "
                        "Police and K9 units showed up. "
                        "Everyone laughed once they realized it was a drink mix. "
                        "Edit: fixed typos."
                    ),
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
    segment_text = "\n".join(line["text"] for line in episode_script["segments"][0]["lines"])
    cold_open_text = "\n".join(line["text"] for line in episode_script["cold_open"]["lines"])

    assert "Setup: Yikes!" not in segment_text
    assert "Setup: How did that happen?" not in segment_text
    assert "Payoff: Edit:" not in segment_text
    assert "C4 as in fruit-punch pre-workout" in segment_text
    assert "Police and K9 units show up" in segment_text
    assert "workplace nickname is C4" in segment_text
    assert "lunchbox.." not in cold_open_text


def test_write_episode_script_rewrites_known_c4_airport_story_as_a_treatment_not_raw_sentences():
    body = (
        "Well, to start off I just want to make mention that this was during my first week of employment with an airport. "
        "I packed my lunch box with a sandwich and a bottle of pre-workout. "
        "The brand of pre-workout was C4. "
        "I told TSA I had some C4 in my lunchbox. "
        "In less then a minute, police and K9 units show up. "
        "Now whenever I see the TSA guy, he joking says C4 as we both laugh."
    )
    outline = {
        "title_angle": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
        "cold_open": {"hook": body, "visual_note": "Airport security hallway."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": body,
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
    spoken_text = "\n".join(
        line["text"]
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    )

    assert "Picture your first week working at an airport." in spoken_text
    assert "Already anxious." in spoken_text
    assert "Well, to start off" not in spoken_text



def test_write_episode_script_tells_known_c4_story_in_scenes_not_labels():
    body = (
        "Well, to start off I just want to make mention that this was during my first week of employment with an airport. "
        "I packed my lunch box with a sandwich and a bottle of pre-workout. "
        "The brand of pre-workout was C4. "
        "I told TSA I had some C4 in my lunchbox. "
        "The TSA agent asked me what I meant by C4. "
        "In less then a minute, police and K9 units show up. "
        "Now whenever I see the TSA guy, he joking says C4 as we both laugh."
    )
    outline = {
        "title_angle": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
        "cold_open": {"hook": body, "visual_note": "Airport security hallway."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": body,
                    "top_comments": [
                        {
                            "comment_id": "c1",
                            "body": "Now you can bring actual C4 and no one would be the wiser",
                            "score": 10,
                        }
                    ],
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
    spoken_lines = [
        line["text"]
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    ]
    spoken_text = "\n".join(spoken_lines)

    assert "The bad sentence:" not in spoken_text
    assert "Escalation:" not in spoken_text
    assert "Payoff:" not in spoken_text
    assert "Comment section button:" not in spoken_text
    assert spoken_lines == [
        "Picture your first week working at an airport.",
        "Already anxious.",
        "You pack lunch. Sandwich, chips, granola bars, pre-workout.",
        "Normal gym goblin behavior. Continue.",
        "Then TSA asks what's in the lunchbox.",
        "No. I know where this is going and I hate it.",
        'He says, "sandwich, chips, granola bars, and C4."',
        "Wait—C4 as in C4?",
        "C4 as in fruit-punch pre-workout, but airport security does not get that footnote yet.",
        "You cannot put the brand name after the snack list like it is a Capri-Sun.",
        "The TSA agent stops on the one word you would hope no TSA agent ever hears.",
        'There is no chill way to say "I brought C4" in an airport.',
        "Police and K9 units show up before he can even open the product photo.",
        "That is not a misunderstanding. That is a lunchbox speedrun to a federal incident.",
        "Eventually they realize it is workout powder, not explosives.",
        "So the threat level drops from national security to man with terrible supplement branding.",
        "Nobody is hurt. Everyone laughs. His new workplace nickname is C4.",
        "You do not recover from that. You just become airport folklore.",
        "A commenter points out he could probably bring actual C4 now and no one would believe him.",
        "The boy who cried pre-workout. Incredible. Terrible, but incredible.",
    ]


def test_write_episode_script_gives_c4_hosts_distinct_comic_roles():
    body = (
        "Well, to start off I just want to make mention that this was during my first week of employment with an airport. "
        "I packed my lunch box with a sandwich and a bottle of pre-workout. "
        "The brand of pre-workout was C4. "
        "I told TSA I had some C4 in my lunchbox. "
        "The TSA agent asked me what I meant by C4. "
        "In less then a minute, police and K9 units show up. "
        "Now whenever I see the TSA guy, he joking says C4 as we both laugh."
    )
    outline = {
        "title_angle": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
        "cold_open": {"hook": body, "visual_note": "Airport security hallway."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": body,
                    "top_comments": [
                        {
                            "comment_id": "c1",
                            "body": "Now you can bring actual C4 and no one would be the wiser",
                            "score": 10,
                        }
                    ],
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
    lines = [
        line
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    ]
    spoken_text = "\n".join(line["text"] for line in lines)
    host_1_text = "\n".join(line["text"] for line in lines if line["speaker"] == "host_1")
    host_2_text = "\n".join(line["text"] for line in lines if line["speaker"] == "host_2")

    assert "C4 as in fruit-punch pre-workout" in host_1_text
    assert "Wait—C4 as in C4?" in host_2_text
    assert "The boy who cried pre-workout. Incredible. Terrible, but incredible." in host_2_text
    assert "There is no chill way" in spoken_text
    assert "The bad sentence:" not in spoken_text
    assert "Comment section button:" not in spoken_text



def test_write_episode_script_builds_c4_story_as_call_and_response_banter():
    body = (
        "I packed my lunch box with a sandwich and a bottle of pre-workout. "
        "The brand of pre-workout was C4. "
        "I told TSA I had some C4 in my lunchbox. "
        "The TSA agent asked me what I meant by C4. "
        "In less then a minute, police and K9 units show up."
    )
    outline = {
        "title_angle": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
        "cold_open": {"hook": body, "visual_note": "Airport security hallway."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": body,
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
    spoken_lines = [
        line["text"]
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    ]

    assert spoken_lines[0:6] == [
        "Picture your first week working at an airport.",
        "Already anxious.",
        "You pack lunch. Sandwich, chips, granola bars, pre-workout.",
        "Normal gym goblin behavior. Continue.",
        "Then TSA asks what's in the lunchbox.",
        "No. I know where this is going and I hate it.",
    ]
    assert spoken_lines[6:10] == [
        'He says, "sandwich, chips, granola bars, and C4."',
        "Wait—C4 as in C4?",
        "C4 as in fruit-punch pre-workout, but airport security does not get that footnote yet.",
        "You cannot put the brand name after the snack list like it is a Capri-Sun.",
    ]



def test_write_episode_script_makes_hosts_answer_each_other_not_trade_monologues():
    body = (
        "I packed my lunch box with a sandwich and a bottle of pre-workout. "
        "The brand of pre-workout was C4. "
        "I told TSA I had some C4 in my lunchbox. "
        "The TSA agent asked me what I meant by C4. "
        "In less then a minute, police and K9 units show up."
    )
    outline = {
        "title_angle": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
        "cold_open": {"hook": body, "visual_note": "Airport security hallway."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": body,
                    "top_comments": [
                        {
                            "comment_id": "c1",
                            "body": "Now you can bring actual C4 and no one would be the wiser",
                            "score": 10,
                        }
                    ],
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
    lines = [
        line
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    ]
    spoken_pairs = [(line["speaker"], line["text"]) for line in lines]

    assert spoken_pairs[0:6] == [
        ("host_1", "Picture your first week working at an airport."),
        ("host_2", "Already anxious."),
        ("host_1", "You pack lunch. Sandwich, chips, granola bars, pre-workout."),
        ("host_2", "Normal gym goblin behavior. Continue."),
        ("host_1", "Then TSA asks what's in the lunchbox."),
        ("host_2", "No. I know where this is going and I hate it."),
    ]
    assert (
        "host_2",
        "Wait—C4 as in C4?",
    ) in spoken_pairs
    wait_index = spoken_pairs.index(("host_2", "Wait—C4 as in C4?"))
    assert spoken_pairs[wait_index + 1] == (
        "host_1",
        "C4 as in fruit-punch pre-workout, but airport security does not get that footnote yet.",
    )
    assert (
        "host_1",
        "Police and K9 units show up before he can even open the product photo.",
    ) in spoken_pairs
    assert (
        "host_2",
        "That is not a misunderstanding. That is a lunchbox speedrun to a federal incident.",
    ) in spoken_pairs
    assert spoken_pairs[-2:] == [
        ("host_1", "A commenter points out he could probably bring actual C4 now and no one would believe him."),
        ("host_2", "The boy who cried pre-workout. Incredible. Terrible, but incredible."),
    ]



def test_write_episode_script_uses_comment_reaction_as_a_beat_when_available():
    outline = {
        "title_angle": "TSA lunchbox disaster",
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU by telling TSA I had C4 in my lunchbox",
                    "subreddit": "tifu",
                    "body": "I accidentally made airport security think my preworkout was an explosive.",
                    "top_comments": [
                        {
                            "comment_id": "c1",
                            "body": "The slogan says explosive energy, but maybe never say that at TSA.",
                            "score": 1200,
                        }
                    ],
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
    segment_text = "\n".join(line["text"] for line in episode_script["segments"][0]["lines"])

    assert "A commenter points out" in segment_text
    assert "Comment section button" not in segment_text
    assert "explosive energy" in segment_text



def test_write_episode_script_adds_cold_open_lines_without_stage_label_prefixes():
    outline = {
        "title_angle": "Messy Reddit stories",
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
            "text": "Today got absurd fast.",
        },
        {
            "speaker": "host_2",
            "text": "And somehow it only gets worse from there.",
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



def test_write_episode_script_adds_outro_lines_without_stage_label_prefixes():
    outline = {
        "title_angle": "Messy Reddit stories",
        "outro": {
            "callback": "Remember the birthday dinner meltdown.",
            "tomorrow_tease": "Tomorrow we get into the pettiest roommate fights.",
            "visual_note": "Outro visual",
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
            "text": "Remember the birthday dinner meltdown.",
        },
        {
            "speaker": "host_2",
            "text": "Tomorrow we get into the pettiest roommate fights.",
        },
    ]


def test_write_episode_script_uses_configured_host_profiles_to_shape_dialogue():
    body = (
        "I packed my lunch box with a sandwich and a bottle of pre-workout. "
        "The brand of pre-workout was C4. "
        "I told TSA I had some C4 in my lunchbox. "
        "The TSA agent asked me what I meant by C4. "
        "In less then a minute, police and K9 units show up."
    )
    outline = {
        "title_angle": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
        "cold_open": {"hook": body, "visual_note": "Airport security hallway."},
        "segments": [
            {
                "position": 1,
                "source": {
                    "reddit_post_id": "p1",
                    "title": "TIFU: By telling airport TSA I had C4 in my lunchbox.",
                    "subreddit": "tifu",
                    "body": body,
                },
            }
        ],
    }
    config = {
        "hosts": {
            "host_1": {
                "key": "narrator",
                "name": "Mara",
                "role": "deadpan_story_driver",
                "personality": "dry setup narrator",
            },
            "host_2": {
                "key": "skeptic",
                "name": "Jules",
                "role": "skeptical_reactor",
                "personality": "suspicious follow-up questioner",
            },
        }
    }

    episode_script = write_episode_script(outline, config)
    spoken_pairs = [
        (line["speaker"], line["text"])
        for section in (episode_script["cold_open"], *episode_script["segments"])
        for line in section["lines"]
    ]

    assert episode_script["host_profiles"] == {
        "narrator": {
            "name": "Mara",
            "role": "deadpan_story_driver",
            "personality": "dry setup narrator",
        },
        "skeptic": {
            "name": "Jules",
            "role": "skeptical_reactor",
            "personality": "suspicious follow-up questioner",
        },
    }
    assert ("skeptic", "Define C4 before the dogs arrive.") in spoken_pairs
    assert ("skeptic", "That lunchbox is now evidence with snacks.") in spoken_pairs
