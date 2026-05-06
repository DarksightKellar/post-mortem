from reddit_automation.pipeline.score import calculate_overall_score, score_candidates, should_keep_candidate


def test_calculate_overall_score_uses_configured_weights():
    weights = {
        "reaction_potential": 0.40,
        "laugh_factor": 0.25,
        "story_payoff": 0.15,
        "clarity_after_rewrite": 0.10,
        "comment_bonus": 0.10,
    }
    subscores = {
        "reaction_potential": 8,
        "laugh_factor": 7,
        "story_payoff": 6,
        "clarity_after_rewrite": 9,
        "comment_bonus": 5,
    }

    overall_score = calculate_overall_score(subscores, weights)

    assert overall_score == 7.25


def test_should_keep_candidate_returns_true_when_thresholds_are_met():
    thresholds = {
        "min_reaction_potential": 8,
        "min_laugh_factor": 7,
        "min_overall_score": 7.2,
    }
    scored_candidate = {
        "reaction_potential": 8,
        "laugh_factor": 7,
        "overall_score": 7.25,
    }

    keep = should_keep_candidate(scored_candidate, thresholds)

    assert keep is True


def test_score_candidates_applies_weights_and_adds_overall_score():
    config = {
        "scoring": {
            "weights": {
                "reaction_potential": 0.40,
                "laugh_factor": 0.25,
                "story_payoff": 0.15,
                "clarity_after_rewrite": 0.10,
                "comment_bonus": 0.10,
            },
            "thresholds": {
                "min_reaction_potential": 8,
                "min_laugh_factor": 7,
                "min_overall_score": 7.2,
            },
        }
    }
    candidates = [
        {
            "reddit_post_id": "abc123",
            "reaction_potential": 8,
            "laugh_factor": 7,
            "story_payoff": 6,
            "clarity_after_rewrite": 9,
            "comment_bonus": 5,
        }
    ]

    scored_candidates = score_candidates(candidates, config)

    assert scored_candidates == [
        {
            "reddit_post_id": "abc123",
            "reaction_potential": 8,
            "laugh_factor": 7,
            "story_payoff": 6,
            "clarity_after_rewrite": 9,
            "comment_bonus": 5,
            "overall_score": 7.25,
            "keep": True,
        }
    ]


def test_score_candidates_returns_candidates_sorted_by_overall_score_descending():
    config = {
        "scoring": {
            "weights": {
                "reaction_potential": 0.40,
                "laugh_factor": 0.25,
                "story_payoff": 0.15,
                "clarity_after_rewrite": 0.10,
                "comment_bonus": 0.10,
            },
            "thresholds": {
                "min_reaction_potential": 1,
                "min_laugh_factor": 1,
                "min_overall_score": 1,
            },
        }
    }
    candidates = [
        {
            "reddit_post_id": "lower",
            "reaction_potential": 6,
            "laugh_factor": 6,
            "story_payoff": 6,
            "clarity_after_rewrite": 6,
            "comment_bonus": 6,
        },
        {
            "reddit_post_id": "higher",
            "reaction_potential": 9,
            "laugh_factor": 8,
            "story_payoff": 7,
            "clarity_after_rewrite": 8,
            "comment_bonus": 7,
        },
    ]

    scored_candidates = score_candidates(candidates, config)

    assert [candidate["reddit_post_id"] for candidate in scored_candidates] == ["higher", "lower"]


def test_score_candidates_scores_unscored_candidates_with_builtin_heuristics():
    config = {
        "scoring": {
            "weights": {
                "reaction_potential": 0.40,
                "laugh_factor": 0.25,
                "story_payoff": 0.15,
                "clarity_after_rewrite": 0.10,
                "comment_bonus": 0.10,
            },
            "thresholds": {
                "min_reaction_potential": 8,
                "min_laugh_factor": 7,
                "min_overall_score": 7.2,
            },
        }
    }
    candidates = [
        {
            "reddit_post_id": "strong",
            "title": "What is the funniest petty revenge you have ever seen?",
            "body": "My roommate kept stealing my food, so I relabeled everything with fake ingredient lists until he stopped.",
            "subreddit": "pettyrevenge",
            "score": 420,
            "comment_count": 87,
            "top_comments": [
                {"body": "This is beautifully unhinged", "score": 120},
                {"body": "Petty and effective. Perfect combo.", "score": 95},
            ],
        }
    ]

    scored_candidates = score_candidates(candidates, config)

    assert scored_candidates[0]["reaction_potential"] >= 8
    assert scored_candidates[0]["laugh_factor"] >= 7
    assert scored_candidates[0]["overall_score"] >= 7.2
    assert scored_candidates[0]["keep"] is True


def test_score_candidates_rejects_low_signal_unscored_candidates_with_builtin_heuristics():
    config = {
        "scoring": {
            "weights": {
                "reaction_potential": 0.40,
                "laugh_factor": 0.25,
                "story_payoff": 0.15,
                "clarity_after_rewrite": 0.10,
                "comment_bonus": 0.10,
            },
            "thresholds": {
                "min_reaction_potential": 8,
                "min_laugh_factor": 7,
                "min_overall_score": 7.2,
            },
        }
    }
    candidates = [
        {
            "reddit_post_id": "weak",
            "title": "Need help",
            "body": "",
            "subreddit": "AskReddit",
            "score": 1,
            "comment_count": 0,
            "top_comments": [],
        }
    ]

    scored_candidates = score_candidates(candidates, config)

    assert scored_candidates[0]["reaction_potential"] < 8
    assert scored_candidates[0]["laugh_factor"] < 7
    assert scored_candidates[0]["overall_score"] < 7.2
    assert scored_candidates[0]["keep"] is False
