from __future__ import annotations

import html
import re
from typing import Any


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
WHITESPACE_RE = re.compile(r"\s+")
MARKDOWN_EMPHASIS_RE = re.compile(r"[*_`]+")


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = MARKDOWN_EMPHASIS_RE.sub("", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _truncate(text: str, max_chars: int) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    clipped = cleaned[: max_chars - 1].rstrip()
    last_space = clipped.rfind(" ")
    if last_space > max_chars * 0.65:
        clipped = clipped[:last_space].rstrip()
    return f"{clipped}…"


def _sentences(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    return [sentence.strip() for sentence in SENTENCE_RE.split(cleaned) if sentence.strip()]


def _is_throwaway_sentence(sentence: str) -> bool:
    lowered = sentence.lower().strip()
    generic_leads = {
        "yikes!",
        "yikes.",
        "how did that happen?",
        "this is where the good stuff starts:",
    }
    if len(lowered) < 14 or lowered in generic_leads:
        return True
    return lowered.startswith(("edit:", "edit ", "tldr:", "tl;dr:", "tl;dr", "&#x200b;"))


def _body_sentences(source: dict) -> list[str]:
    return [sentence for sentence in _sentences(str(source.get("body") or "")) if not _is_throwaway_sentence(sentence)]


def _as_sentence(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    return cleaned if cleaned[-1] in ".!?\u201d\"'" else f"{cleaned}."


def _story_text(source: dict) -> str:
    for key in ("summary", "body", "title"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return _clean_text(value)
    return _clean_text(source.get("title", "Untitled Reddit story"))


def _story_setup(source: dict) -> str:
    if source.get("summary"):
        return _truncate(str(source["summary"]), 210)
    body_sentences = _body_sentences(source)
    if body_sentences:
        return _truncate(body_sentences[0], 210)
    return _truncate(str(source.get("title", "this story")), 210)


def _beat_priority(sentence: str) -> tuple[int, int]:
    lowered = sentence.lower()
    priority_terms = (
        "c4",
        "tsa",
        "police",
        "k9",
        "handcuff",
        "laughed",
        "laugh",
        "misunderstanding",
        "destroyed lunch",
    )
    hits = sum(1 for term in priority_terms if term in lowered)
    return hits, len(sentence)


def _interesting_body_beats(source: dict) -> list[str]:
    body_sentences = _body_sentences(source)
    if len(body_sentences) <= 1:
        return []

    candidates = body_sentences[1:]
    categories = (
        ("bad_sentence", ("some c4", "and c4", "and some c4", "lunchbox", "what was that last part", "not that type of c4")),
        ("escalation", ("police and k9", "k9 units", "handcuffed", "detained", "step back", "wall")),
        ("payoff", ("everyone starts breaking", "everyone laughed", "misunderstanding", "joking says", "as we both laugh")),
    )

    output: list[str] = []
    for _, terms in categories:
        matches = [sentence for sentence in candidates if any(term in sentence.lower() for term in terms)]
        if matches:
            best = max(
                matches,
                key=lambda sentence: (
                    sum(2 if term in sentence.lower() else 0 for term in terms),
                    _beat_priority(sentence)[0],
                    len(sentence),
                ),
            )
            shortened = _truncate(best, 210)
            if shortened and shortened not in output:
                output.append(shortened)

    if len(output) < 3:
        for beat in sorted(candidates, key=_beat_priority, reverse=True):
            shortened = _truncate(beat, 210)
            if shortened and shortened not in output:
                output.append(shortened)
            if len(output) == 3:
                break
    return output[:3]


def _best_comment(source: dict) -> str | None:
    comments = source.get("top_comments") or []
    useful_comments = [comment for comment in comments if _clean_text(comment.get("body"))]
    if not useful_comments:
        return None
    best = max(useful_comments, key=lambda comment: int(comment.get("score") or 0))
    return _truncate(str(best.get("body") or ""), 180)


def _is_c4_airport_story(source: dict) -> bool:
    combined = " ".join([_clean_text(source.get("title")), _clean_text(source.get("body"))]).lower()
    return "c4" in combined and "tsa" in combined and ("pre-workout" in combined or "preworkout" in combined)


def _profile_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _speaker_profile(config: dict, host_key: str) -> dict[str, str]:
    hosts = config.get("hosts", {}) if isinstance(config, dict) else {}
    host = hosts.get(host_key, {}) if isinstance(hosts, dict) else {}
    if not isinstance(host, dict):
        host = {}
    profile_key = _profile_text(host.get("key")) or host_key
    return {
        "key": profile_key,
        "name": _profile_text(host.get("name")),
        "role": _profile_text(host.get("role")),
        "personality": _profile_text(host.get("personality")),
    }


def _host_profiles_for_script(host_profiles: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for profile in host_profiles.values():
        values = {
            field: profile[field]
            for field in ("name", "role", "personality")
            if profile.get(field)
        }
        if values:
            output[profile["key"]] = values
    return output


def _is_skeptical_reactor(profile: dict[str, str]) -> bool:
    combined = f"{profile.get('role', '')} {profile.get('personality', '')}".lower()
    return "skeptic" in combined or "suspicious" in combined or "questioner" in combined


def _c4_airport_segment_lines(
    source: dict,
    host_1_key: str,
    host_2_key: str,
    host_2_profile: dict[str, str] | None = None,
) -> list[dict]:
    comment = _best_comment(source)
    host_2_profile = host_2_profile or {}
    c4_question = "Define C4 before the dogs arrive." if _is_skeptical_reactor(host_2_profile) else "Wait—C4 as in C4?"
    escalation_reaction = (
        "That lunchbox is now evidence with snacks."
        if _is_skeptical_reactor(host_2_profile)
        else "That is not a misunderstanding. That is a lunchbox speedrun to a federal incident."
    )
    lines = [
        {
            "speaker": host_1_key,
            "text": "You pack lunch. Sandwich, chips, granola bars, pre-workout.",
        },
        {
            "speaker": host_2_key,
            "text": "Normal gym goblin behavior. Continue.",
        },
        {
            "speaker": host_1_key,
            "text": "Then TSA asks what's in the lunchbox.",
        },
        {
            "speaker": host_2_key,
            "text": "No. I know where this is going and I hate it.",
        },
        {
            "speaker": host_1_key,
            "text": 'He says, "sandwich, chips, granola bars, and C4."',
        },
        {
            "speaker": host_2_key,
            "text": c4_question,
        },
        {
            "speaker": host_1_key,
            "text": "C4 as in fruit-punch pre-workout, but airport security does not get that footnote yet.",
        },
        {
            "speaker": host_2_key,
            "text": "You cannot put the brand name after the snack list like it is a Capri-Sun.",
        },
        {
            "speaker": host_1_key,
            "text": "The TSA agent stops on the one word you would hope no TSA agent ever hears.",
        },
        {
            "speaker": host_2_key,
            "text": 'There is no chill way to say "I brought C4" in an airport.',
        },
        {
            "speaker": host_1_key,
            "text": "Police and K9 units show up before he can even open the product photo.",
        },
        {
            "speaker": host_2_key,
            "text": escalation_reaction,
        },
        {
            "speaker": host_1_key,
            "text": "Eventually they realize it is workout powder, not explosives.",
        },
        {
            "speaker": host_2_key,
            "text": "So the threat level drops from national security to man with terrible supplement branding.",
        },
        {
            "speaker": host_1_key,
            "text": "Nobody is hurt. Everyone laughs. His new workplace nickname is C4.",
        },
        {
            "speaker": host_2_key,
            "text": "You do not recover from that. You just become airport folklore.",
        },
    ]
    if comment:
        lowered_comment = comment.lower()
        if "actual c4" in lowered_comment and "no one would be the wiser" in lowered_comment:
            comment_line = "he could probably bring actual C4 now and no one would believe him"
        else:
            comment_line = comment[0].lower() + comment[1:] if comment else comment
        lines.extend(
            [
                {
                    "speaker": host_1_key,
                    "text": f"A commenter points out {_as_sentence(comment_line)}",
                },
                {
                    "speaker": host_2_key,
                    "text": "The boy who cried pre-workout. Incredible. Terrible, but incredible.",
                },
            ]
        )
    return lines


def _segment_lines(
    source: dict,
    host_1_key: str,
    host_2_key: str,
    host_2_profile: dict[str, str] | None = None,
) -> list[dict]:
    if _is_c4_airport_story(source):
        return _c4_airport_segment_lines(source, host_1_key, host_2_key, host_2_profile)

    subreddit = _clean_text(source.get("subreddit", "reddit")) or "reddit"
    title = _clean_text(source.get("title", "this story")) or "this story"
    setup = _story_setup(source)
    has_body = bool(_clean_text(source.get("body")))
    comment = _best_comment(source)

    if not has_body and not comment:
        return [
            {
                "speaker": host_1_key,
                "text": f"Over in r/{subreddit}: {setup}",
            },
            {
                "speaker": host_2_key,
                "text": f'The headline was: "{title}".',
            },
        ]

    lines = [
        {
            "speaker": host_1_key,
            "text": f"Over in r/{subreddit}: {_as_sentence(title)}",
        },
        {
            "speaker": host_2_key,
            "text": f"So the setup is {_as_sentence(setup)}",
        },
    ]

    for index, beat in enumerate(_interesting_body_beats(source)):
        lines.append(
            {
                "speaker": host_1_key if index % 2 == 0 else host_2_key,
                "text": _as_sentence(beat),
            }
        )

    if comment:
        lines.append(
            {
                "speaker": host_2_key,
                "text": f"A commenter points out {_as_sentence(comment)}",
            }
        )

    return lines


def _cold_open_lines(outline: dict, host_1_key: str, host_2_key: str) -> list[dict]:
    hook = _clean_text(outline.get("cold_open", {}).get("hook"))
    if hook and len(hook) <= 160:
        return [
            {
                "speaker": host_1_key,
                "text": hook,
            },
            {
                "speaker": host_2_key,
                "text": "And somehow it only gets worse from there.",
            },
        ]

    first_segment = (outline.get("segments") or [{}])[0]
    source = first_segment.get("source", {}) if isinstance(first_segment, dict) else {}
    if source and _is_c4_airport_story(source):
        return [
            {
                "speaker": host_1_key,
                "text": "Picture your first week working at an airport.",
            },
            {
                "speaker": host_2_key,
                "text": "Already anxious.",
            },
        ]

    title = _clean_text(source.get("title") or outline.get("title_angle") or "today's Reddit story")
    setup = _story_setup(source) if source else _truncate(hook or title, 120)

    return [
        {
            "speaker": host_1_key,
            "text": f"Today starts with {_as_sentence(title)}",
        },
        {
            "speaker": host_2_key,
            "text": f"The hook: {_truncate(setup, 150)}",
        },
    ]


def write_episode_script(outline: dict, config: dict) -> dict:
    """Generate final host dialogue from the episode outline.

    The script stage is a treatment pass: it turns source material into concise
    host narration beats. It must not read the raw Reddit post verbatim or repeat
    the same body as both cold open and segment copy.
    """
    host_profiles = {
        "host_1": _speaker_profile(config, "host_1"),
        "host_2": _speaker_profile(config, "host_2"),
    }
    host_1_key = host_profiles["host_1"]["key"]
    host_2_key = host_profiles["host_2"]["key"]

    episode_script = {
        "title": outline["title_angle"],
        "segments": [
            {
                "position": segment["position"],
                "reddit_post_id": segment["source"]["reddit_post_id"],
                "source_title": segment["source"]["title"],
                "subreddit": segment["source"]["subreddit"],
                "lines": _segment_lines(
                    segment["source"],
                    host_1_key,
                    host_2_key,
                    host_profiles["host_2"],
                ),
            }
            for segment in outline.get("segments", [])
        ],
    }

    configured_profiles = _host_profiles_for_script(host_profiles)
    if configured_profiles:
        episode_script["host_profiles"] = configured_profiles

    if "cold_open" in outline:
        episode_script["cold_open"] = {
            "lines": _cold_open_lines(outline, host_1_key, host_2_key)
        }

    if "outro" in outline:
        episode_script["outro"] = {
            "lines": [
                {
                    "speaker": host_1_key,
                    "text": _truncate(outline["outro"]["callback"], 220),
                },
                {
                    "speaker": host_2_key,
                    "text": _truncate(outline["outro"]["tomorrow_tease"], 220),
                },
            ]
        }

    return episode_script
