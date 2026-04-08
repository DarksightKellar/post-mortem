from reddit_automation.clients.llm_client import LLMClient


SCORE_KEYS = (
    "reaction_potential",
    "laugh_factor",
    "story_payoff",
    "clarity_after_rewrite",
    "comment_bonus",
)


def _build_scoring_payload(candidate: dict) -> dict:
    """Shape a single candidate for the LLM scoring prompt."""
    return {
        "title": candidate.get("title", ""),
        "body": candidate.get("body", ""),
        "subreddit": candidate.get("subreddit", ""),
        "score": candidate.get("score", 0),
        "comment_count": candidate.get("comment_count", 0),
        "comments": [
            {
                "body": comment.get("body", ""),
                "score": comment.get("score", 0),
            }
            for comment in candidate.get("top_comments", [])
        ],
    }


def score_candidates_with_llm(candidates: list[dict], config: dict) -> list[dict]:
    """Score candidates by calling the LLM for subscores, then apply weighted math.

    TODO: Wire this into run_daily.py when the LLM client is implemented.
    For now, run_daily.py uses score_pre_fetched_candidates() (no LLM path).
    """
    llm = LLMClient(config)
    scored_results = []

    for candidate in candidates:
        payload = _build_scoring_payload(candidate)
        llm_subscores = llm.complete_json("scoring", payload)

        scored_candidate = dict(candidate)
        for score_key, score_value in llm_subscores.items():
            scored_candidate[score_key] = score_value

        scored_candidate["overall_score"] = calculate_overall_score(
            llm_subscores, config["scoring"]["weights"]
        )
        scored_candidate["keep"] = meets_quality_threshold(
            scored_candidate, config["scoring"]["thresholds"]
        )
        scored_results.append(scored_candidate)

    return sorted(scored_results, key=lambda c: c["overall_score"], reverse=True)


def calculate_overall_score(subscores: dict, weights: dict) -> float:
    return sum(subscores[key] * weights[key] for key in weights)


def meets_quality_threshold(scored_candidate: dict, thresholds: dict) -> bool:
    return (
        scored_candidate["reaction_potential"] >= thresholds["min_reaction_potential"]
        and scored_candidate["laugh_factor"] >= thresholds["min_laugh_factor"]
        and scored_candidate["overall_score"] >= thresholds["min_overall_score"]
    )


def should_keep_candidate(scored_candidate: dict, thresholds: dict) -> bool:
    return meets_quality_threshold(scored_candidate, thresholds)


def _candidates_have_prefetched_scores(candidates: list[dict]) -> bool:
    return all(all(score_key in candidate for score_key in SCORE_KEYS) for candidate in candidates)


def score_candidates(candidates: list[dict], config: dict) -> list[dict]:
    if _candidates_have_prefetched_scores(candidates):
        return score_pre_fetched_candidates(candidates, config)
    return score_candidates_with_llm(candidates, config)


def score_pre_fetched_candidates(candidates: list[dict], config: dict) -> list[dict]:
    """Score candidates using subscores already present in the candidate dict.

    Used by run_daily.py before the LLM client is wired in. Reads weights
    from config["scoring"]["weights"] and thresholds from
    config["scoring"]["thresholds"].
    """
    weights = config["scoring"]["weights"]
    thresholds = config["scoring"]["thresholds"]
    scored_results = []

    for candidate in candidates:
        scored_candidate = dict(candidate)
        subscores = {score_key: candidate[score_key] for score_key in weights}
        scored_candidate["overall_score"] = calculate_overall_score(subscores, weights)
        scored_candidate["keep"] = meets_quality_threshold(scored_candidate, thresholds)
        scored_results.append(scored_candidate)

    return sorted(scored_results, key=lambda candidate: candidate["overall_score"], reverse=True)
