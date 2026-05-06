import json

import pytest

from reddit_automation.clients.comfy_qwen_tts_client import ComfyQwenTTSClient


class FakeResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self.payload = payload
        self.status = status

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def json_response(data):
    return FakeResponse(json.dumps(data).encode("utf-8"))


def test_comfy_qwen_tts_client_submits_custom_voice_workflow_and_downloads_audio(tmp_path):
    requests = []

    def fake_urlopen(request, timeout=None):
        url = getattr(request, "full_url", request)
        body = getattr(request, "data", None)
        requests.append({"url": url, "body": body, "timeout": timeout})
        if url == "http://comfy.test/prompt":
            return json_response({"prompt_id": "prompt-1", "node_errors": {}})
        if url == "http://comfy.test/history/prompt-1":
            return json_response(
                {
                    "prompt-1": {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {
                            "2": {
                                "audio": [
                                    {
                                        "filename": "postmortem_00001_.mp3",
                                        "subfolder": "postmortem",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                    }
                }
            )
        if url.startswith("http://comfy.test/view?"):
            return FakeResponse(b"mp3-bytes")
        raise AssertionError(f"Unexpected URL: {url}")

    config = {
        "output_dir": str(tmp_path),
        "tts": {
            "comfy_qwen_tts": {
                "base_url": "http://comfy.test",
                "model_size": "0.6B",
                "language": "English",
                "device": "auto",
                "precision": "bf16",
                "attention": "auto",
                "max_new_tokens": 768,
                "do_sample": False,
                "timeout_seconds": 12,
            }
        },
        "hosts": {
            "host_1": {
                "key": "host_1",
                "voice_id": "Ryan",
                "voice_instruct": "Dry host voice with crisp podcast pacing.",
            }
        },
    }
    client = ComfyQwenTTSClient(
        config,
        urlopen=fake_urlopen,
        sleep_fn=lambda seconds: None,
        client_id_factory=lambda: "client-1",
    )

    output_path = client.generate("host_1", "This line should be synthesized.")

    assert output_path.endswith(".mp3")
    assert (tmp_path / "tts" / "qwen").is_dir()
    assert open(output_path, "rb").read() == b"mp3-bytes"

    prompt_request = requests[0]
    assert prompt_request["url"] == "http://comfy.test/prompt"
    assert prompt_request["timeout"] == 12
    payload = json.loads(prompt_request["body"].decode("utf-8"))
    assert payload["client_id"] == "client-1"
    workflow = payload["prompt"]
    assert workflow["1"]["class_type"] == "AILab_Qwen3TTSCustomVoice_Advanced"
    assert workflow["1"]["inputs"] == {
        "text": "This line should be synthesized.",
        "speaker": "Ryan",
        "model_size": "0.6B",
        "device": "auto",
        "precision": "bf16",
        "language": "English",
        "instruct": "Dry host voice with crisp podcast pacing.",
        "max_new_tokens": 768,
        "do_sample": False,
        "top_p": 0.9,
        "top_k": 50,
        "temperature": 0.9,
        "repetition_penalty": 1.0,
        "attention": "auto",
        "unload_models": False,
        "seed": -1,
    }
    assert workflow["2"] == {
        "class_type": "SaveAudioMP3",
        "inputs": {
            "audio": ["1", 0],
            "filename_prefix": "postmortem/host_1",
        },
    }


def test_comfy_qwen_tts_client_uses_safe_qwen_defaults_not_edge_voice_ids(tmp_path):
    client = ComfyQwenTTSClient(
        {
            "output_dir": str(tmp_path),
            "tts": {"comfy_qwen_tts": {"base_url": "http://comfy.test"}},
            "hosts": {
                "host_1": {"voice_id": "en-US-GuyNeural", "personality": "dry"},
                "host_2": {"voice_id": "en-US-AnaNeural", "personality": "sharp"},
            },
        },
        urlopen=lambda request, timeout=None: json_response({}),
    )

    host_1_workflow = client._build_workflow("host_1", "One line.")
    host_2_workflow = client._build_workflow("host_2", "Another line.")
    unknown_workflow = client._build_workflow("unknown/../../speaker", "Fallback line.")

    assert host_1_workflow["1"]["inputs"]["speaker"] == "Ryan"
    assert host_2_workflow["1"]["inputs"]["speaker"] == "Serena"
    assert unknown_workflow["1"]["inputs"]["speaker"] == "Ryan"
    assert unknown_workflow["2"]["inputs"]["filename_prefix"] == "postmortem/unknown_speaker"


def test_comfy_qwen_tts_client_raises_clear_error_when_comfy_execution_fails(tmp_path):
    def fake_urlopen(request, timeout=None):
        url = getattr(request, "full_url", request)
        if url == "http://comfy.test/prompt":
            return json_response({"prompt_id": "prompt-1", "node_errors": {}})
        if url == "http://comfy.test/history/prompt-1":
            return json_response(
                {
                    "prompt-1": {
                        "status": {
                            "completed": True,
                            "status_str": "error",
                            "messages": [
                                [
                                    "execution_error",
                                    {
                                        "node_id": "1",
                                        "exception_type": "RuntimeError",
                                        "exception_message": "Qwen model is missing",
                                    },
                                ]
                            ],
                        },
                        "outputs": {},
                    }
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")

    client = ComfyQwenTTSClient(
        {
            "output_dir": str(tmp_path),
            "tts": {"comfy_qwen_tts": {"base_url": "http://comfy.test"}},
            "hosts": {"host_1": {"key": "host_1", "voice_id": "Ryan"}},
        },
        urlopen=fake_urlopen,
        sleep_fn=lambda seconds: None,
        client_id_factory=lambda: "client-1",
    )

    with pytest.raises(RuntimeError, match="node 1.*Qwen model is missing"):
        client.generate("host_1", "This will fail.")
