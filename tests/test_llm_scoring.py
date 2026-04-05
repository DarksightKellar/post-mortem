"""Tests for LLM-powered candidate scoring.

score_candidates_with_llm() calls the LLM once per candidate with the thread title,
body, and top comments, then merges the returned subscores into each candidate before
delegating to the weighted-math scoring step.
"""

from unittest.mock import patch
from reddit_automation.pipeline.score import score_candidates_with_llm


def _make_candidate(post_id, title="Test title"):
    return {
        "reddit_post_id": post_id,
        "title": title,
        "body": "Some body text here",
        "subreddit": "tifu",
        "top_comments": [
            {"comment_id": "c1", "body": "Comment one", "score": 10},
            {"comment_id": "c2", "body": "Comment two", "score": 5},
        ],
    }


def test_score_candidates_with_llm_calls_llm_per_candidate(monkeypatch):
    """LLM should be called once per candidate with the thread + comments payload."""
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
        },
        "prompts": {
            "scoring_system_file": "prompts/scoring_system.txt",
            "scoring_user_template_file": "prompts/scoring_user.txt",
        },
    }

    candidates = [_make_candidate("p1"), _make_candidate("p2")]

    scored_llm = []

    def fake_llm_complete(self, prompt_name, payload):
        scored_llm.append((prompt_name, payload["title"], len(payload.get("comments", []))))
        return {
            "reaction_potential": 9,
            "laugh_factor": 8,
            "story_payoff": 7,
            "clarity_after_rewrite": 8,
            "comment_bonus": 6,
        }

    from reddit_automation.clients import llm_client
    monkeypatch.setattr(llm_client.LLMClient, "complete_json", fake_llm_complete)

    result = score_candidates_with_llm(candidates, config)

    # LLM called once per candidate
    assert len(scored_llm) == 2
    assert scored_llm[0] == ("scoring", "Test title", 2)
    assert scored_llm[1] == ("scoring", "Test title", 2)

    # Results have subscores, overall_score, and keep flag
    assert len(result) == 2
    for r in result:
        assert r["reaction_potential"] == 9
        assert r["laugh_factor"] == 8
        assert "overall_score" in r
        assert "keep" in r


def test_score_candidates_with_llm_rejects_empty_body_and_comments(monkeypatch):
    """Candidates with no body and no comments should be given low clarity and rejected."""
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
        },
        "prompts": {
            "scoring_system_file": "prompts/scoring_system.txt",
            "scoring_user_template_file": "prompts/scoring_user.txt",
        },
    }

    empty_candidate = {
        "reddit_post_id": "p_empty",
        "title": "Title only",
        "body": "",
        "subreddit": "AskReddit",
        "top_comments": [],
    }

    def fake_llm_complete(self, prompt_name, payload):
        return {
            "reaction_potential": 3,
            "laugh_factor": 2,
            "story_payoff": 2,
            "clarity_after_rewrite": 1,
            "comment_bonus": 0,
        }

    from reddit_automation.clients import llm_client
    monkeypatch.setattr(llm_client.LLMClient, "complete_json", fake_llm_complete)

    result = score_candidates_with_llm([empty_candidate], config)

    assert len(result) == 1
    assert result[0]["keep"] is False
    assert result[0]["overall_score"] < 7.2


def test_score_candidates_with_llm_passes_through_to_weighted_scoring(monkeypatch):
    """After LLM scoring, the weighted math and keep flag must match expected values."""
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
        },
        "prompts": {
            "scoring_system_file": "prompts/scoring_system.txt",
            "scoring_user_template_file": "prompts/scoring_user.txt",
        },
    }

    # Scores: 10*0.4 + 8*0.25 + 7*0.15 + 9*0.1 + 6*0.1 = 4+2+1.05+0.9+0.6 = 8.55
    def fake_llm_complete(self, prompt_name, payload):
        return {
            "reaction_potential": 10,
            "laugh_factor": 8,
            "story_payoff": 7,
            "clarity_after_rewrite": 9,
            "comment_bonus": 6,
        }

    from reddit_automation.clients import llm_client
    monkeypatch.setattr(llm_client.LLMClient, "complete_json", fake_llm_complete)

    result = score_candidates_with_llm([_make_candidate("p1")], config)

    assert abs(result[0]["overall_score"] - 8.55) < 0.01
    assert result[0]["keep"] is True
