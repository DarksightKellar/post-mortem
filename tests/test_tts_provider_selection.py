import json

from reddit_automation.clients.tts_client import TTSClient


def test_tts_client_delegates_to_comfy_qwen_tts_provider(monkeypatch):
    calls = []

    class StubComfyQwenTTSClient:
        def __init__(self, config):
            calls.append(("init", config))

        def generate(self, speaker_key, text):
            calls.append(("generate", speaker_key, text))
            return "/tmp/qwen-line.mp3"

    monkeypatch.setattr(
        "reddit_automation.clients.tts_client.ComfyQwenTTSClient",
        StubComfyQwenTTSClient,
    )
    config = {"tts": {"provider": "comfy_qwen_tts"}}

    client = TTSClient(config)
    output_path = client.generate("host_1", "Comfy should speak this line.")

    assert output_path == "/tmp/qwen-line.mp3"
    assert calls == [
        ("init", config),
        ("generate", "host_1", "Comfy should speak this line."),
    ]


def test_tts_client_posts_to_elevenlabs_text_to_speech_api(monkeypatch, tmp_path):
    requests = []

    class StubResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"mp3-bytes"

    def stub_urlopen(request, timeout):
        requests.append({"request": request, "timeout": timeout})
        return StubResponse()

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-api-key")
    monkeypatch.setattr("urllib.request.urlopen", stub_urlopen)
    config = {
        "output_dir": str(tmp_path),
        "hosts": {
            "host_1": {
                "key": "host_1",
                "voice_id": "edge-voice-kept-for-fallback",
                "elevenlabs_voice_id": "eleven-host-1",
            }
        },
        "tts": {
            "provider": "elevenlabs",
            "elevenlabs": {
                "api_key_env": "ELEVENLABS_API_KEY",
                "model_id": "eleven_multilingual_v2",
                "output_format": "mp3_44100_128",
                "timeout_seconds": 30,
            },
        },
    }

    output_path = TTSClient(config).generate("host_1", "ElevenLabs should speak this line.")

    assert requests[0]["timeout"] == 30
    request = requests[0]["request"]
    assert request.full_url == (
        "https://api.elevenlabs.io/v1/text-to-speech/eleven-host-1?output_format=mp3_44100_128"
    )
    assert request.headers["Xi-api-key"] == "test-api-key"
    assert request.headers["Accept"] == "audio/mpeg"
    assert request.headers["Content-type"] == "application/json"
    assert json.loads(request.data.decode("utf-8")) == {
        "text": "ElevenLabs should speak this line.",
        "model_id": "eleven_multilingual_v2",
    }
    with open(output_path, "rb") as audio_file:
        assert audio_file.read() == b"mp3-bytes"
