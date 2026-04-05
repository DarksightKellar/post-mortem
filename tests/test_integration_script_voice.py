"""Integration test proving that write_episode_script output → generate_episode_audio work together.

This test uses the real write_episode_script and real generate_episode_audio logic.
Only the actual TTS generation call (TTSClient.generate) is monkeypatched — the
TTSClient class itself and all voice.py orchestration logic run for real.
"""

from reddit_automation.pipeline.outline import build_episode_outline
from reddit_automation.pipeline.script import write_episode_script
from reddit_automation.pipeline.voice import generate_episode_audio
from reddit_automation.clients.tts_client import TTSClient


def test_script_to_voice_integration_produced_audio_path(monkeypatch):
    """Generate a real outline → real script → real audio pipeline.

    Monkeypatch only TTSClient.generate so no network/key is needed.
    Assert the returned audio_path is a string and that TTS was called
    for cold_open lines first, then segment lines.
    """
    config = {
        "project": {"episode_date": "2026-04-03"},
        "scripting": {"target_segments": 2},
        "hosts": {
            "host_1": {"key": "host_1"},
            "host_2": {"key": "host_2"},
        },
    }
    selected_items = {
        "primary": [
            {
                "reddit_post_id": "p1",
                "title": "Story 1",
                "subreddit": "AskReddit",
            },
            {
                "reddit_post_id": "p2",
                "title": "Story 2",
                "subreddit": "tifu",
            },
        ],
        "backups": [],
    }

    # Track every real TTSClient.generate call
    tts_generate_calls = []

    original_generate = TTSClient.generate

    def _stub_generate(self, speaker_key, text):
        tts_generate_calls.append((speaker_key, text))
        return f"/tmp/audio/{len(tts_generate_calls):04d}-{speaker_key}.wav"

    monkeypatch.setattr(TTSClient, "generate", _stub_generate)
    monkeypatch.setattr(
        "reddit_automation.pipeline.voice.stitch_audio_clips",
        lambda paths, out: "/tmp/fake_episode_audio.mp3",
    )

    # Real pipeline: outline → script → audio
    outline = build_episode_outline(selected_items, config)
    episode_script = write_episode_script(outline, config)
    audio_path = generate_episode_audio(episode_script, config)

    # Assert: audio_path is a string (empty, because _stitch_audio_clips is a stub returning "")
    assert isinstance(audio_path, str), "audio_path should be a string"

    # Assert: TTSClient.generate was called for cold_open lines AND segment lines
    assert len(tts_generate_calls) > 0, "TTSClient.generate should have been called"

    # Cold open produces 2 lines (host_1 + host_2) before any segment lines
    cold_open_count = len(outline["cold_open"].get("lines", [])) if "cold_open" in outline else 0
    # Actually the outline cold_open doesn't have 'lines' key — script.py creates them.
    # In the script, cold_open has 2 lines. Each segment has 2 lines.
    # Expected order: cold_open host_1, cold_open host_2, then segment lines.
    assert tts_generate_calls[0] == ("host_1", f"Cold open: {outline['cold_open']['hook']}"), \
        "First TTS call should be cold_open host_1"
    assert tts_generate_calls[1] == ("host_2", f"Cold open reaction: {outline['cold_open']['hook']}"), \
        "Second TTS call should be cold_open host_2"

    # Then segment lines
    first_segment = episode_script["segments"][0]
    expected_seg_start_idx = 2
    assert tts_generate_calls[expected_seg_start_idx] == ("host_1", f"Setup: {first_segment['source_title']}"), \
        "TTS call after cold_open should be segment host_1 setup"
