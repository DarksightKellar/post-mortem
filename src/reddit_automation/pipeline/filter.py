from __future__ import annotations

from typing import Iterable


DEFAULT_BANNED_TERMS = {
    "politics": ["election", "senate", "congress", "democrat", "republican", "trump", "biden"],
    "culture_war": ["woke", "sjw", "cancel culture", "gender war"],
    "tragedy": ["funeral", "terminal illness", "grief", "tragedy"],
    "abuse": ["abuse", "assault", "molested", "violent partner"],
    "death": ["died", "death", "murder", "killed", "suicide"],
    "nsfw": ["onlyfans", "porn", "nudes", "sex", "nsfw"],
}


def _combined_text(candidate: dict) -> str:
    comment_text = " ".join(comment.get("body", "") for comment in candidate.get("top_comments", []))
    return " ".join([
        candidate.get("title", ""),
        candidate.get("body", ""),
        comment_text,
    ]).lower()


def passes_hard_filters(candidate: dict, config: dict) -> bool:
    filters = config.get("filters", {})
    text = _combined_text(candidate)

    for category in filters.get("exclude_categories", []):
        for term in DEFAULT_BANNED_TERMS.get(category, []):
            if term in text:
                return False

    if filters.get("exclude_low_context", True):
        has_body = bool((candidate.get("body") or "").strip())
        has_comments = any((c.get("body") or "").strip() for c in candidate.get("top_comments", []))
        if not has_body and not has_comments:
            return False

    return True


def dedupe_candidates(candidates: Iterable[dict]) -> list[dict]:
    seen = set()
    output = []
    for candidate in candidates:
        key = (candidate.get("subreddit"), (candidate.get("title") or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(candidate)
    return output


def filter_candidates(raw_candidates: list[dict], config: dict) -> list[dict]:
    survivors = [candidate for candidate in raw_candidates if passes_hard_filters(candidate, config)]
    if config.get("filters", {}).get("dedupe_similar_posts", True):
        survivors = dedupe_candidates(survivors)
    return survivors
