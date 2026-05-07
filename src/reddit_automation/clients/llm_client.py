from __future__ import annotations

from math import log10
from typing import Any


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 1)


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


class LLMClient:
    """Deterministic local scorer used by the scoring pipeline.

    The project still routes scoring through ``complete_json('scoring', payload)`` so the
    orchestration contract stays stable, but the implementation is local and does not
    require an external LLM service.
    """

    REACTION_WORDS = (
        "funniest",
        "funny",
        "wild",
        "insane",
        "petty",
        "revenge",
        "chaos",
        "awkward",
        "embarrassing",
        "unhinged",
    )
    LAUGH_WORDS = (
        "funniest",
        "funny",
        "laughed",
        "laugh",
        "hilarious",
        "petty",
        "revenge",
        "joke",
        "ridiculous",
        "unhinged",
    )
    STORY_WORDS = (
        "because",
        "when",
        "after",
        "then",
        "until",
        "finally",
        "roommate",
        "coworker",
        "boss",
        "neighbor",
    )
    COMEDY_COMMUNITIES = {
        "askreddit",
        "amitheasshole",
        "tifu",
        "facepalm",
        "maliciouscompliance",
        "pettyrevenge",
        "antiwork",
        "greentext",
    }

    def __init__(self, config: dict):
        self.config = config

    def complete_json(self, prompt_name: str, payload: dict[str, Any]) -> dict[str, float]:
        if prompt_name != "scoring":
            raise ValueError(f"Unsupported prompt_name: {prompt_name}")

        title = (payload.get("title") or "").strip()
        body = (payload.get("body") or "").strip()
        source_community = (payload.get("source_community") or "").strip().lower()
        comments = payload.get("comments") or []
        score = max(float(payload.get("score") or 0), 0.0)
        comment_count = max(float(payload.get("comment_count") or 0), 0.0)

        comment_bodies = " ".join((comment.get("body") or "") for comment in comments)
        combined_text = " ".join(part for part in (title, body, comment_bodies) if part)
        text_length = len(combined_text)
        community_bonus = 0.6 if source_community in self.COMEDY_COMMUNITIES else 0.0
        score_signal = min(log10(score + 1.0) * 2.2, 3.2)
        comment_signal = min(log10(comment_count + 1.0) * 1.8, 2.4)
        body_signal = min(len(body) / 120.0, 2.0)
        comment_quality_signal = min(sum(float(comment.get("score") or 0) for comment in comments) / 180.0, 2.0)
        reaction_hits = min(_count_keyword_hits(combined_text, self.REACTION_WORDS), 3)
        laugh_hits = min(_count_keyword_hits(combined_text, self.LAUGH_WORDS), 3)
        story_hits = min(_count_keyword_hits(combined_text, self.STORY_WORDS), 3)
        punctuation_signal = 0.3 if any(mark in title for mark in ("?", "!")) else 0.0

        reaction_potential = _clamp_score(
            2.2 + score_signal + (comment_signal * 0.7) + (reaction_hits * 0.55) + community_bonus + punctuation_signal
        )
        laugh_factor = _clamp_score(
            1.8 + (laugh_hits * 1.0) + (comment_signal * 0.5) + (comment_quality_signal * 0.35) + community_bonus
        )
        story_payoff = _clamp_score(
            2.0 + body_signal + (story_hits * 0.65) + (comment_signal * 0.45) + min(text_length / 220.0, 1.8)
        )
        clarity_after_rewrite = _clamp_score(
            1.0
            + (2.5 if body else 0.0)
            + (1.5 if comments else 0.0)
            + min(text_length / 180.0, 3.2)
            - (1.2 if not body and not comments else 0.0)
        )
        comment_bonus = _clamp_score((comment_signal * 1.8) + (comment_quality_signal * 1.6))

        return {
            "reaction_potential": reaction_potential,
            "laugh_factor": laugh_factor,
            "story_payoff": story_payoff,
            "clarity_after_rewrite": clarity_after_rewrite,
            "comment_bonus": comment_bonus,
        }
