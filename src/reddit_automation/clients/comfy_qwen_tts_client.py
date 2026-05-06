from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen as default_urlopen


QWEN_VOICE_DEFAULTS = {
    "host_1": "Ryan",
    "host_2": "Serena",
}

QWEN_PRESET_VOICES = {
    "Aiden",
    "Dylan",
    "Eric",
    "Ono_Anna",
    "Ryan",
    "Serena",
    "Sohee",
    "Uncle_Fu",
    "Vivian",
}


class ComfyQwenTTSClient:
    """HTTP client for generating one TTS line through a local ComfyUI-QwenTTS workflow."""

    def __init__(
        self,
        config: dict,
        *,
        urlopen: Callable | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        client_id_factory: Callable[[], str] | None = None,
    ):
        self.config = config or {}
        tts_config = self.config.get("tts", {}) if isinstance(self.config, dict) else {}
        self.qwen_config = tts_config.get("comfy_qwen_tts", {}) if isinstance(tts_config, dict) else {}
        self.base_url = str(self.qwen_config.get("base_url", "http://127.0.0.1:8188")).rstrip("/")
        self.timeout_seconds = float(self.qwen_config.get("timeout_seconds", 900))
        self.poll_interval_seconds = float(self.qwen_config.get("poll_interval_seconds", 1.0))
        self.max_poll_attempts = int(self.qwen_config.get("max_poll_attempts", 900))
        self.urlopen = urlopen or default_urlopen
        self.sleep_fn = sleep_fn or time.sleep
        self.client_id_factory = client_id_factory or (lambda: str(uuid.uuid4()))
        self.output_dir = Path(
            self.qwen_config.get("output_dir")
            or Path(self.config.get("output_dir", "/tmp")) / "tts" / "qwen"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, speaker_key: str, text: str) -> str:
        if not text or not text.strip():
            raise ValueError("TTS text must be non-empty")

        output_path = self._local_output_path(speaker_key, text)
        if output_path.exists():
            return str(output_path)

        workflow = self._build_workflow(speaker_key, text)
        prompt_id = self._submit_prompt(workflow)
        output_ref = self._wait_for_audio_output(prompt_id)
        audio_bytes = self._download_output(output_ref)
        output_path.write_bytes(audio_bytes)
        return str(output_path)

    def _local_output_path(self, speaker_key: str, text: str) -> Path:
        digest_source = json.dumps(
            {
                "speaker_key": speaker_key,
                "text": text,
                "speaker": self._speaker_for(speaker_key),
                "instruct": self._instruct_for(speaker_key),
                "model_size": self.qwen_config.get("model_size", "0.6B"),
                "language": self.qwen_config.get("language", "English"),
                "max_new_tokens": self.qwen_config.get("max_new_tokens", 768),
                "do_sample": self.qwen_config.get("do_sample", False),
                "seed": self.qwen_config.get("seed", -1),
            },
            sort_keys=True,
        )
        digest = hashlib.md5(digest_source.encode("utf-8")).hexdigest()[:12]
        return self.output_dir / f"{self._safe_speaker_key(speaker_key)}_{digest}.mp3"

    def _build_workflow(self, speaker_key: str, text: str) -> dict[str, dict[str, Any]]:
        return {
            "1": {
                "class_type": "AILab_Qwen3TTSCustomVoice_Advanced",
                "inputs": {
                    "text": text,
                    "speaker": self._speaker_for(speaker_key),
                    "model_size": self.qwen_config.get("model_size", "0.6B"),
                    "device": self.qwen_config.get("device", "auto"),
                    "precision": self.qwen_config.get("precision", "bf16"),
                    "language": self.qwen_config.get("language", "English"),
                    "instruct": self._instruct_for(speaker_key),
                    "max_new_tokens": self.qwen_config.get("max_new_tokens", 768),
                    "do_sample": self.qwen_config.get("do_sample", False),
                    "top_p": self.qwen_config.get("top_p", 0.9),
                    "top_k": self.qwen_config.get("top_k", 50),
                    "temperature": self.qwen_config.get("temperature", 0.9),
                    "repetition_penalty": self.qwen_config.get("repetition_penalty", 1.0),
                    "attention": self.qwen_config.get("attention", "auto"),
                    "unload_models": self.qwen_config.get("unload_models", False),
                    "seed": self.qwen_config.get("seed", -1),
                },
            },
            "2": {
                "class_type": "SaveAudioMP3",
                "inputs": {
                    "audio": ["1", 0],
                    "filename_prefix": f"postmortem/{self._safe_speaker_key(speaker_key)}",
                },
            },
        }

    def _speaker_for(self, speaker_key: str) -> str:
        host = self._host_for(speaker_key)
        qwen_voice_id = host.get("qwen_voice_id")
        if qwen_voice_id:
            return str(qwen_voice_id)
        voice_id = host.get("voice_id")
        if voice_id in QWEN_PRESET_VOICES:
            return str(voice_id)
        return QWEN_VOICE_DEFAULTS.get(speaker_key, "Ryan")

    def _safe_speaker_key(self, speaker_key: str) -> str:
        safe_key = re.sub(r"[^A-Za-z0-9_-]+", "_", speaker_key).strip("_")
        return safe_key or "speaker"

    def _instruct_for(self, speaker_key: str) -> str:
        host = self._host_for(speaker_key)
        return str(host.get("voice_instruct") or host.get("personality") or "")

    def _host_for(self, speaker_key: str) -> dict[str, Any]:
        hosts = self.config.get("hosts", {}) if isinstance(self.config, dict) else {}
        if not isinstance(hosts, dict):
            return {}
        if speaker_key in hosts and isinstance(hosts[speaker_key], dict):
            return hosts[speaker_key]
        for host_key, host in hosts.items():
            if isinstance(host, dict) and host.get("key", host_key) == speaker_key:
                return host
        return {}

    def _submit_prompt(self, workflow: dict[str, dict[str, Any]]) -> str:
        payload = {
            "prompt": workflow,
            "client_id": self.client_id_factory(),
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = self._read_json(request)
        node_errors = response.get("node_errors") or {}
        if node_errors:
            raise RuntimeError(f"ComfyUI rejected QwenTTS workflow: {node_errors}")
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI response did not include prompt_id: {response}")
        return str(prompt_id)

    def _wait_for_audio_output(self, prompt_id: str) -> dict[str, str]:
        for _ in range(self.max_poll_attempts):
            history = self._read_json(f"{self.base_url}/history/{prompt_id}")
            entry = history.get(prompt_id, history) if isinstance(history, dict) else {}
            status = entry.get("status", {}) if isinstance(entry, dict) else {}
            status_str = status.get("status_str")
            if status_str == "error":
                self._raise_execution_error(status)
            if status.get("completed") and status_str in (None, "success"):
                return self._extract_audio_output(entry.get("outputs", {}))
            self.sleep_fn(self.poll_interval_seconds)
        raise TimeoutError(f"Timed out waiting for ComfyUI QwenTTS prompt {prompt_id}")

    def _raise_execution_error(self, status: dict[str, Any]) -> None:
        for message in status.get("messages", []) or []:
            if not isinstance(message, (list, tuple)) or len(message) != 2:
                continue
            kind, details = message
            if kind != "execution_error" or not isinstance(details, dict):
                continue
            node_id = details.get("node_id", "unknown")
            error_type = details.get("exception_type", "ComfyUIError")
            error_message = details.get("exception_message", "unknown error")
            raise RuntimeError(f"ComfyUI QwenTTS failed at node {node_id}: {error_type}: {error_message}")
        raise RuntimeError(f"ComfyUI QwenTTS failed: {status}")

    def _extract_audio_output(self, outputs: dict[str, Any]) -> dict[str, str]:
        for node_output in (outputs or {}).values():
            if not isinstance(node_output, dict):
                continue
            for key in ("audio", "audios"):
                audio_refs = node_output.get(key)
                if isinstance(audio_refs, list) and audio_refs:
                    ref = audio_refs[0]
                    if isinstance(ref, dict) and ref.get("filename"):
                        return {
                            "filename": str(ref.get("filename", "")),
                            "subfolder": str(ref.get("subfolder", "")),
                            "type": str(ref.get("type", "output")),
                        }
        raise RuntimeError(f"ComfyUI QwenTTS completed without audio output: {outputs}")

    def _download_output(self, output_ref: dict[str, str]) -> bytes:
        query = urlencode(output_ref)
        with self.urlopen(f"{self.base_url}/view?{query}", timeout=self.timeout_seconds) as response:
            data = response.read()
        if not data:
            raise RuntimeError(f"ComfyUI returned empty audio for {output_ref}")
        return data

    def _read_json(self, request_or_url: Any) -> dict[str, Any]:
        with self.urlopen(request_or_url, timeout=self.timeout_seconds) as response:
            raw = response.read()
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))
