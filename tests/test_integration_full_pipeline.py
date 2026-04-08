"""Complete end-to-end pipeline test:

    fetch → filter → store → score → select → outline → script → voice →
    visuals → render → publish → notify

Only external I/O boundaries are stubbed (TTS, stitch, render, YouTube, Telegram).
All business logic runs for real.
"""

import os
import json
from unittest.mock import patch
from reddit_automation.pipeline.fetch import fetch_candidates
from reddit_automation.pipeline.filter import filter_candidates
from reddit_automation.pipeline.store import store_candidates
from reddit_automation.pipeline.score import score_candidates_with_llm
from reddit_automation.pipeline.select import select_episode_items
from reddit_automation.pipeline.outline import build_episode_outline
from reddit_automation.pipeline.script import write_episode_script
from reddit_automation.pipeline.voice import generate_episode_audio
from reddit_automation.pipeline.visuals import build_visual_plan
from reddit_automation.pipeline.render import render_episode_video
from reddit_automation.pipeline.publish import publish_episode
from reddit_automation.pipeline.notify import send_run_notification
from reddit_automation.storage.db import Database
from reddit_automation.utils.paths import SCHEMA_SQL_PATH


def _make_submission(reddit_id, subreddit, title, body, comments, created_utc=1000000):
    return {
        "id": reddit_id,
        "subreddit": subreddit,
        "title": title,
        "selftext": body,
        "url": f"https://reddit.com/r/{subreddit}/posts/{reddit_id}",
        "author": f"u/test_{reddit_id}",
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
        "author": f"u/c_{comment_id}",
        "created_utc": 1000000,
    }


def _load_config():
    import yaml
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config", "config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def test_full_pipeline_fetch_through_publish(tmp_path, monkeypatch):
    """Runs data ingestion + media + publish with only I/O stubbed.

    Stubs: TTS generate, stitch_audio, render_backend, YouTubeClient.upload, Telegram urlopen.
    Everything else is real business logic.
    """

    # --- Build 5 submissions ---
    rich_comments = [
        _make_comment("c1", "This is the funniest thing I've read all week", score=200),
        _make_comment("c2", "The plot twist at the end gets me every time", score=150),
        _make_comment("c3", "I had something similar happen to me once", score=80),
    ]

    submissions = [
        _make_submission("p1", "tifu", "TIFU by accidentally starting a neighbourhood drama",
                         "So this happened last weekend when I meant to compliment my neighbour's lawn...",
                         rich_comments, created_utc=1100000),
        _make_submission("p2", "AskReddit", "What's your hottest take on office culture?",
                         "I think the 4-day work week is overrated and here is my long rant about it",
                         [_make_comment("c4", "Hard disagree on this one", score=100),
                          _make_comment("c5", "This makes no sense honestly", score=50)],
                         created_utc=1200000),
        _make_submission("p3", "MaliciousCompliance", "Manager said no overtime, so I left mid-deadline",
                         "Our boss explicitly said no working past 5pm to finish this project, so I packed up at 5",
                         [_make_comment("c6", "Classic malicious compliance, love it", score=300),
                          _make_comment("c7", "The follow-up better be good", score=200)],
                         created_utc=1300000),
        _make_submission("p4", "facepalm", "Cashier handed me cash while I was paying with card",
                         "I tapped my card, the machine said approved, then the cashier hands me a twenty back",
                         [_make_comment("c8", "Free money basically", score=80)],
                         created_utc=1400000),
        _make_submission("p5", "greentext", "That time I accidentally became a meme",
                         "Long story short, someone snapped a photo and it went everywhere",
                         [_make_comment("c9", "Living the dream", score=60),
                          _make_comment("c10", "At least you're internet famous now", score=40)],
                         created_utc=1500000),
    ]

    config = _load_config()
    config["reddit_test_data"] = {"submissions": submissions}
    config["project"]["episode_date"] = "2026-04-03"
    config["alerts"]["telegram_bot_token"] = "test-token"
    config["alerts"]["telegram_chat_id"] = "test-chat"

    # --- Stage 1: Fetch ---
    raw = fetch_candidates(config)
    assert len(raw) == 5
    for c in raw:
        assert "reddit_post_id" in c
        assert "top_comments" in c

    # --- Stage 2: Filter ---
    survived = filter_candidates(raw, config)
    assert len(survived) >= 2, f"Expected at least 2 survivors, got {len(survived)}"

    # --- Stage 3: Store ---
    db = Database(str(tmp_path / "test.db"))
    db.init_schema(SCHEMA_SQL_PATH)
    store_result = store_candidates(survived, db)
    assert store_result["stored_candidates"] == len(survived)
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
    assert len(scored) == len(survived)
    for s in scored:
        assert "overall_score" in s
        assert "keep" in s

    # --- Stage 5: Select ---
    selection = select_episode_items(scored, config)
    assert len(selection["primary"]) >= 1

    # --- Stage 6: Outline ---
    outline = build_episode_outline(selection, config)
    assert "segments" in outline
    assert "title_angle" in outline
    assert "cold_open" in outline
    assert "outro" in outline
    assert len(outline["segments"]) >= 1

    # --- Stage 7: Script ---
    episode_script = write_episode_script(outline, config)
    assert "title" in episode_script
    assert "segments" in episode_script
    assert "cold_open" in episode_script
    assert "outro" in episode_script

    # --- Stage 8: Voice (stub TTS generation + stitching) ---
    tts_calls = []

    def stub_tts_generate(self, speaker_key, text):
        tts_calls.append((speaker_key, text))
        return str(tmp_path / f"{len(tts_calls):04d}-{speaker_key}.mp3")

    with patch(
        "reddit_automation.clients.tts_client.TTSClient.generate",
        stub_tts_generate,
    ):
        with patch(
            "reddit_automation.pipeline.voice.stitch_audio_clips",
            return_value=str(tmp_path / "final_audio.mp3")
        ) as mock_stitch:
            rendered_audio_path = generate_episode_audio(episode_script, config)

    assert rendered_audio_path == str(tmp_path / "final_audio.mp3")
    assert mock_stitch.call_count == 1
    assert tts_calls, "voice stage should invoke TTS generation"

    # --- Stage 9: Visuals ---
    visual_plan = build_visual_plan(outline, config)
    assert len(visual_plan["scenes"]) >= 2  # at minimum: title_card + outro
    assert visual_plan["scenes"][0]["type"] == "title_card"

    # --- Stage 10: Render (stub scene generation + render backend) ---
    config["project"]["render_dir"] = str(tmp_path / "renders")

    def stub_generate_scene_images(visual_plan, config):
        return []

    with patch(
        "reddit_automation.pipeline.render.generate_scene_images", stub_generate_scene_images,
    ):
        with patch(
            "reddit_automation.pipeline.render.render_video"
        ) as mock_render:
            render_result = render_episode_video(rendered_audio_path, visual_plan, config)

    assert render_result.endswith(".mp4")
    assert mock_render.call_count == 1

    # --- Stage 11: Publish (stub YouTube) ---
    from reddit_automation.clients import youtube_client
    with patch.object(
        youtube_client.YouTubeClient, "upload",
        return_value={
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
            "status": "uploaded",
            "privacy_status": "private",
        }
    ):
        publish_result = publish_episode(render_result, {"title": episode_script["title"]}, config)
    assert publish_result["video_id"] == "abc123"
    assert publish_result["status"] == "uploaded"

    # --- Stage 12: Notify (stub Telegram HTTP) ---
    telegram_requests = []

    class StubTelegramResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"ok": True}).encode("utf-8")

    def stub_urlopen(request):
        telegram_requests.append(request)
        return StubTelegramResponse()

    with patch("urllib.request.urlopen", stub_urlopen):
        send_run_notification("success", f"Episode published: {episode_script['title']}", config)

    assert len(telegram_requests) == 1

    # --- Final assertions ---
    # Pipeline survived end-to-end with real business logic at every stage
    assert len(selection["primary"]) >= 1
    assert len(outline["segments"]) >= 1
    assert len(episode_script["segments"]) >= 1
    assert len(visual_plan["scenes"]) >= 2
    assert rendered_audio_path.endswith(".mp3")
    assert render_result.endswith(".mp4")
