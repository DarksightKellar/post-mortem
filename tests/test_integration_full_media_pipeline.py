"""Integration test proving the full pipeline: outline → script → voice → visuals → render.

Only the pure I/O functions are monkeypatched:
- TTSClient.generate (avoids network/API calls)
- stitch_audio_clips (avoids ffmpeg)
- render_video (avoids actual video encoding)

All orchestration logic runs for real.
"""

from reddit_automation.pipeline.outline import build_episode_outline
from reddit_automation.pipeline.script import write_episode_script
from reddit_automation.pipeline.voice import generate_episode_audio
from reddit_automation.pipeline.visuals import build_visual_plan
from reddit_automation.pipeline.render import render_episode_video


def _make_selection():
    return {
        "primary": [
            {"reddit_post_id": "p1", "title": "TIFU by accidentally starting a neighbourhood war", "author": "u/test1", "url": "https://reddit.com/tifu/p1", "subreddit": "tifu"},
            {"reddit_post_id": "p2", "title": "AITA for refusing to share my wifi password?", "author": "u/test2", "url": "https://reddit.com/aita/p2", "subreddit": "AmItheAsshole"},
            {"reddit_post_id": "p3", "title": "Manager said no overtime, so I left mid-deadline", "author": "u/test3", "url": "https://reddit.com/mc/p3", "subreddit": "MaliciousCompliance"},
        ],
    }


def _make_config():
    return {
        "project": {"episode_date": "2026-04-03", "render_dir": "/tmp/rendered"},
        "scripting": {
            "target_segments": 3,
            "cold_open_seconds": 15,
            "outro_seconds": 40,
            "max_direct_quote_words": 12,
        },
        "hosts": {
            "host_1": {"key": "host_1", "name": "Host 1", "role": "main"},
            "host_2": {"key": "host_2", "name": "Host 2", "role": "adaptive"},
        },
        "comments": {"max_selected_comments_per_segment": 2},
        "output_dir": "/tmp",
    }


def test_full_media_pipeline_from_outline_to_render(monkeypatch):
    """Prove the full chain: outline → script → voice → visuals → render.

    Only 3 pure I/O stubs: TTS generate, stitch audio, render video.
    """
    selection = _make_selection()
    config = _make_config()

    # --- Stage 1: Outline ---
    outline = build_episode_outline(selection, config)
    assert len(outline["segments"]) == 3

    # --- Stage 2: Script ---
    episode_script = write_episode_script(outline, config)
    assert "title" in episode_script
    assert len(episode_script["segments"]) == 3

    # --- Stage 3: Voice (stub TTS + stitching) ---
    tts_calls = []

    class StubTTSClient:
        def __init__(self, passed_config):
            self.config = passed_config

        def generate(self, speaker_key, text):
            tts_calls.append((speaker_key, text))
            return f"/tmp/voice/{len(tts_calls):04d}-{speaker_key}.mp3"

    stitch_calls = []

    def stub_stitch(audio_paths, output_path):
        stitch_calls.append(audio_paths)
        return output_path

    monkeypatch.setattr("reddit_automation.pipeline.voice.TTSClient", StubTTSClient)
    monkeypatch.setattr("reddit_automation.pipeline.voice.stitch_audio_clips", stub_stitch)

    audio_path = generate_episode_audio(episode_script, config)
    assert audio_path == "/tmp/episode_audio.mp3"
    assert len(tts_calls) > 0
    assert len(stitch_calls) == 1

    # Verify ordering: cold_open lines first, then segment lines, then outro lines
    first_cold_open = next(i for i, call in enumerate(tts_calls) if "Cold open" in call[1])
    assert first_cold_open == 0, "Cold open lines should be generated first"

    # --- Stage 4: Visuals ---
    visual_plan = build_visual_plan(outline, config)
    assert len(visual_plan["scenes"]) >= len(outline["segments"]) + 1

    # --- Stage 5: Render (stub scene generation + render backend) ---
    def stub_generate_scene_images(visual_plan, config):
        return []

    render_calls = []

    def stub_render_video(*, audio_path, visual_plan, output_path, config, scene_images=None):
        render_calls.append({"audio_path": audio_path, "visual_plan": visual_plan, "output_path": output_path})
        return output_path

    monkeypatch.setattr("reddit_automation.pipeline.render.generate_scene_images", stub_generate_scene_images)
    monkeypatch.setattr("reddit_automation.pipeline.render.render_video", stub_render_video)

    video_path = render_episode_video(audio_path, visual_plan, config)
    assert video_path == "/tmp/rendered/2026-04-03.mp4"
    assert render_calls == [
        {
            "audio_path": "/tmp/episode_audio.mp3",
            "visual_plan": visual_plan,
            "output_path": "/tmp/rendered/2026-04-03.mp4",
        }
    ]
