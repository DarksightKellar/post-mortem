from reddit_automation.pipeline.voice import generate_episode_audio


def test_generate_episode_audio_generates_and_stitches_single_segment_line(monkeypatch):
    script = {
        "title": "Placeholder: Funniest threads today",
        "segments": [
            {
                "position": 1,
                "reddit_post_id": "p1",
                "source_title": "First story",
                "subreddit": "AskReddit",
                "lines": [
                    {
                        "speaker": "host_1",
                        "text": "Setup: First story",
                    }
                ],
            }
        ],
    }
    config = {"hosts": {"host_1": {"key": "host_1"}}}

    tts_calls = []
    stitch_calls = []

    class StubTTSClient:
        def __init__(self, passed_config):
            assert passed_config == config

        def generate(self, speaker_key, text):
            tts_calls.append((speaker_key, text))
            return "/tmp/voice/0001-host_1.wav"

    def stub_stitch_audio_clips(audio_paths, output_path="/tmp/voice/episode.wav"):
        stitch_calls.append(audio_paths)
        return "/tmp/voice/episode.wav"

    monkeypatch.setattr("reddit_automation.pipeline.voice.TTSClient", StubTTSClient)
    monkeypatch.setattr(
        "reddit_automation.pipeline.voice.stitch_audio_clips",
        stub_stitch_audio_clips,
    )

    audio_path = generate_episode_audio(script, config)

    assert tts_calls == [("host_1", "Setup: First story")]
    assert stitch_calls == [["/tmp/voice/0001-host_1.wav"]]
    assert audio_path == "/tmp/voice/episode.wav"



def test_generate_episode_audio_includes_cold_open_lines_before_segment_lines(monkeypatch):
    script = {
        "title": "Placeholder: Funniest threads today",
        "cold_open": {
            "lines": [
                {
                    "speaker": "host_1",
                    "text": "Cold open: Today got absurd fast.",
                },
                {
                    "speaker": "host_2",
                    "text": "Cold open reaction: Today got absurd fast.",
                },
            ]
        },
        "segments": [
            {
                "position": 1,
                "reddit_post_id": "p1",
                "source_title": "First story",
                "subreddit": "AskReddit",
                "lines": [
                    {
                        "speaker": "host_1",
                        "text": "Setup: First story",
                    }
                ],
            }
        ],
    }
    config = {
        "hosts": {
            "host_1": {"key": "host_1"},
            "host_2": {"key": "host_2"},
        }
    }

    tts_calls = []
    stitch_calls = []

    class StubTTSClient:
        def __init__(self, passed_config):
            assert passed_config == config

        def generate(self, speaker_key, text):
            tts_calls.append((speaker_key, text))
            return f"/tmp/voice/{len(tts_calls):04d}-{speaker_key}.wav"

    def stub_stitch_audio_clips(audio_paths, output_path="/tmp/voice/episode.wav"):
        stitch_calls.append(audio_paths)
        return "/tmp/voice/episode.wav"

    monkeypatch.setattr("reddit_automation.pipeline.voice.TTSClient", StubTTSClient)
    monkeypatch.setattr(
        "reddit_automation.pipeline.voice.stitch_audio_clips",
        stub_stitch_audio_clips,
    )

    audio_path = generate_episode_audio(script, config)

    assert tts_calls == [
        ("host_1", "Cold open: Today got absurd fast."),
        ("host_2", "Cold open reaction: Today got absurd fast."),
        ("host_1", "Setup: First story"),
    ]
    assert stitch_calls == [[
        "/tmp/voice/0001-host_1.wav",
        "/tmp/voice/0002-host_2.wav",
        "/tmp/voice/0003-host_1.wav",
    ]]
    assert audio_path == "/tmp/voice/episode.wav"



def test_generate_episode_audio_appends_outro_lines_after_segment_lines(monkeypatch):
    script = {
        "title": "Placeholder: Funniest threads today",
        "segments": [
            {
                "position": 1,
                "reddit_post_id": "p1",
                "source_title": "First story",
                "subreddit": "AskReddit",
                "lines": [
                    {
                        "speaker": "host_1",
                        "text": "Setup: First story",
                    }
                ],
            }
        ],
        "outro": {
            "lines": [
                {
                    "speaker": "host_2",
                    "text": "Tease: Tomorrow gets even messier.",
                }
            ]
        },
    }
    config = {
        "hosts": {
            "host_1": {"key": "host_1"},
            "host_2": {"key": "host_2"},
        }
    }

    tts_calls = []
    stitch_calls = []

    class StubTTSClient:
        def __init__(self, passed_config):
            assert passed_config == config

        def generate(self, speaker_key, text):
            tts_calls.append((speaker_key, text))
            return f"/tmp/voice/{len(tts_calls):04d}-{speaker_key}.wav"

    def stub_stitch_audio_clips(audio_paths, output_path="/tmp/voice/episode.wav"):
        stitch_calls.append(audio_paths)
        return "/tmp/voice/episode.wav"

    monkeypatch.setattr("reddit_automation.pipeline.voice.TTSClient", StubTTSClient)
    monkeypatch.setattr(
        "reddit_automation.pipeline.voice.stitch_audio_clips",
        stub_stitch_audio_clips,
    )

    audio_path = generate_episode_audio(script, config)

    assert tts_calls == [
        ("host_1", "Setup: First story"),
        ("host_2", "Tease: Tomorrow gets even messier."),
    ]
    assert stitch_calls == [[
        "/tmp/voice/0001-host_1.wav",
        "/tmp/voice/0002-host_2.wav",
    ]]
    assert audio_path == "/tmp/voice/episode.wav"
