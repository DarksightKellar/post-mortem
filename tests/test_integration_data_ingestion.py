"""Integration test covering the entire data ingestion half of the pipeline:

    fetch → filter → store → score → select → outline

Each step uses real implementations. The only external dependency (Reddit API)
is stubbed by feeding test data through the config, which is how RedditClient
is designed to work.
"""

import os
import json
from reddit_automation.pipeline.fetch import fetch_candidates
from reddit_automation.pipeline.filter import filter_candidates
from reddit_automation.pipeline.store import store_candidates
from reddit_automation.pipeline.score import score_candidates_with_llm
from reddit_automation.pipeline.select import select_episode_items
from reddit_automation.pipeline.outline import build_episode_outline
from reddit_automation.storage.db import Database
from reddit_automation.utils.paths import SCHEMA_SQL_PATH


def _make_submission(reddit_id, subreddit, title, body, comments, created_utc=1000000):
    """Build a minimal Reddit submission dict for the RedditClient test data path."""
    return {
        "id": reddit_id,
        "subreddit": subreddit,
        "title": title,
        "selftext": body,
        "url": f"https://reddit.com/r/{subreddit}/posts/{reddit_id}",
        "author": f"u/test_author_{reddit_id}",
        "created_utc": created_utc,
        "score": 500,
        "num_comments": len(comments),
        "comments": comments,
    }


def _make_comment(comment_id, body, score=10):
    return {
        "id": comment_id,
        "body": body,
        "score": score,
        "author": f"u/commenter_{comment_id}",
        "created_utc": 1000000,
    }


def _load_config():
    """Load real config.yaml and wire in test data."""
    import yaml
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config", "config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


def test_full_data_ingestion_chain(tmp_path, monkeypatch):
    """Fetch → filter → store → score → select → outline with real implementations.

    Feeds 5 crafted submissions through the entire ingestion chain:
      - id1: Clean, high-quality post (should survive and score high)
      - id2: Contains banned term "election" (should be filtered out)
      - id3: Clean post, medium quality (should survive)
      - id4: Clean post, high quality (should survive)
      - id5: NSFW content (should be filtered out)
      - id6: Duplicate title of id3 in same subreddit (should be deduped)

    After filtering we expect id1, id3, id4 to remain.
    After scoring & selection we expect 3 primary items (config default).
    """

    comments_rich = [
        _make_comment("c1", "This is a hilarious story, I can't stop laughing", score=200),
        _make_comment("c2", "The plot twist at the end was incredible", score=150),
        _make_comment("c3", "I had a similar experience last week", score=80),
        _make_comment("c4", "Best post I've read all month", score=60),
        _make_comment("c5", "TIL that this actually happens a lot", score=40),
    ]

    submissions = [
        # id1: Clean, high-signal post with great comments
        _make_submission("post_1", "tifu", "TIFU by accidentally starting a neighbourhood war",
                         "So this happened last weekend. I meant to compliment my neighbour's lawn...",
                         comments_rich, created_utc=1100000),

        # id2: Politics content (should be filtered)
        _make_submission("post_2", "AskReddit", "What do you think about the latest election debate?",
                         "I watched the whole thing and here are my thoughts on the candidates",
                         [_make_comment("c6", "I think the senator made great points", score=100),
                          _make_comment("c7", "The election commission should do better", score=50)],
                         created_utc=1200000),

        # id3: Clean post, decent content
        _make_submission("post_3", "AmItheAsshole", "AITA for refusing to share my wifi password?",
                         "My neighbour keeps asking for my wifi password and I keep saying no",
                         [_make_comment("c8", "NTA, it's your property", score=120),
                          _make_comment("c9", "Just get a guest network", score=90)],
                         created_utc=1300000),

        # id4: Clean post, another good one
        _make_submission("post_4", "MaliciousCompliance", "Boss said no overtime, so I left a project unfinished",
                         "My manager said we're not allowed to work overtime to meet this deadline, so I left at 5pm exactly",
                         [_make_comment("c10", "Classic MC, he set himself up for this", score=300),
                          _make_comment("c11", "The follow-up must be good", score=200),
                          _make_comment("c12", "I love when management policies backfire like this", score=150)],
                         created_utc=1400000),

        # id5: NSFW content (should be filtered)
        _make_submission("post_5", "AskReddit", "Rate my outfit for date night",
                         "Going out tonight, thinking of wearing something that's not nsfw at all",
                         [_make_comment("c13", "Looks great!", score=50)],
                         created_utc=1500000),

        # id6: Duplicate of id3's title in same subreddit (should be deduped)
        _make_submission("post_6", "AmItheAsshole", "AITA for refusing to share my wifi password?",
                         "I know this has been asked before but my situation is different",
                         [_make_comment("c14", "Still NTA though", score=30)],
                         created_utc=1600000),
    ]

    config = _load_config()
    config["reddit_test_data"] = {"submissions": submissions}
    config["project"]["episode_date"] = "2026-04-03"

    # --- Stage 1: Fetch ---
    raw = fetch_candidates(config)
    # 6 submissions normalized to 6 candidates with top_comments
    assert len(raw) == 6
    for candidate in raw:
        assert "reddit_post_id" in candidate
        assert "top_comments" in candidate
        assert "title" in candidate
        assert "subreddit" in candidate

    # --- Stage 2: Filter ---
    survived = filter_candidates(raw, config)
    # post_2 banned (election), post_5 banned (nsfw), post_6 dedup of post_3
    # post_4 body + comments rich enough, post_1 rich enough
    # We expect post_1, post_3, post_4 to survive = 3
    survivor_ids = [c["reddit_post_id"] for c in survived]
    assert "post_1" in survivor_ids, "post_1 should survive filtering"
    assert "post_3" in survivor_ids, "post_3 should survive filtering"
    assert "post_4" in survivor_ids, "post_4 should survive filtering"
    assert "post_2" not in survivor_ids, "post_2 should be filtered (politics)"
    assert "post_5" not in survivor_ids, "post_5 should be filtered (nsfw)"
    assert "post_6" not in survivor_ids, "post_6 should be deduped"
    assert len(survived) == 3

    # --- Stage 3: Store ---
    db = Database(str(tmp_path / "test.db"))
    db.init_schema(SCHEMA_SQL_PATH)
    store_result = store_candidates(survived, db)
    assert store_result["stored_candidates"] == 3
    assert store_result["stored_comments"] > 0

    # --- Stage 4: Score (LLM step mocked, business logic real) ---
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

    scored = score_candidates_with_llm(survived, config)
    assert len(scored) == 3
    # All three have scoring subscores injected above
    # Check ordering: highest overall_score first
    assert scored[0]["overall_score"] >= scored[1]["overall_score"] >= scored[2]["overall_score"]
    for s in scored:
        assert "overall_score" in s
        assert "keep" in s

    # --- Stage 5: Select ---
    selection = select_episode_items(scored, config)
    assert "primary" in selection
    assert "backups" in selection
    # 3 keep-qualifying candidates, config wants 3 primaries
    num_keep = sum(1 for s in scored if s["keep"])
    assert len(selection["primary"]) == min(3, num_keep)

    # --- Stage 6: Outline ---
    # Only test outline if we have primaries
    if selection["primary"]:
        outline = build_episode_outline(selection, config)
        assert "segments" in outline
        assert "selection" in outline
        assert "episode_date" in outline
        assert "title_angle" in outline
        assert "cold_open" in outline
        assert "outro" in outline
        assert len(outline["segments"]) == 3
        # Segments should be in order and contain the source data
        for seg in outline["segments"]:
            assert "position" in seg
            assert "source" in seg
            assert "visual_notes" in seg
        # Selection should contain the primary items
        assert len(outline["selection"]["primary_items"]) == 3
