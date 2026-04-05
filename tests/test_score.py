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
