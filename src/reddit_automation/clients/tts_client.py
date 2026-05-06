from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
import urllib.request

from reddit_automation.clients.comfy_qwen_tts_client import ComfyQwenTTSClient


class TTSClient:
    """Config-selected TTS client.

    Defaults to edge-tts; can delegate to ComfyUI QwenTTS or call ElevenLabs.
    """

    def __init__(self, config: dict):
        self.config = config
        tts_config = config.get("tts", {}) if isinstance(config, dict) else {}
        self._provider = tts_config.get("provider", "edge_tts") if isinstance(tts_config, dict) else "edge_tts"
        self._delegate = None
        if self._provider == "comfy_qwen_tts":
            self._delegate = ComfyQwenTTSClient(config)
            return
        if self._provider not in {"edge_tts", "elevenlabs"}:
            raise ValueError(f"Unsupported TTS provider: {self._provider}")

        hosts = config.get("hosts", {}) if isinstance(config, dict) else {}
        self._speaker_id_map = {
            host.get("key", host_key): self._voice_id_for_provider(host)
            for host_key, host in hosts.items()
            if isinstance(host, dict) and self._voice_id_for_provider(host)
        }
        self._speaker_id_map.setdefault("host_1", "en-US-GuyNeural")
        self._speaker_id_map.setdefault("host_2", "en-US-AnaNeural")

    def generate(self, speaker_key: str, text: str) -> str:
        """Generate audio for one line and return the path."""
        if self._delegate is not None:
            return self._delegate.generate(speaker_key, text)
        if self._provider == "elevenlabs":
            return self._generate_with_elevenlabs(speaker_key, text)
        return self._generate_with_edge_tts(speaker_key, text)

    def _voice_id_for_provider(self, host: dict) -> str | None:
        if self._provider == "elevenlabs":
            return host.get("elevenlabs_voice_id") or host.get("voice_id")
        return host.get("voice_id")

    def _generate_with_edge_tts(self, speaker_key: str, text: str) -> str:
        import asyncio

        voice = self._speaker_id_map.get(speaker_key, "en-US-GuyNeural")
        output_dir = pathlib.Path(tempfile.gettempdir()) / "reddit_automation_tts"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"{speaker_key}_{self._safe_hash(text)}.mp3")

        import edge_tts

        asyncio.run(edge_tts.Communicate(text, voice).save(output_path))
        return output_path

    def _generate_with_elevenlabs(self, speaker_key: str, text: str) -> str:
        elevenlabs_config = self._elevenlabs_config()
        api_key_env = elevenlabs_config.get("api_key_env", "ELEVENLABS_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing ElevenLabs API key environment variable: {api_key_env}")

        voice_id = self._speaker_id_map.get(speaker_key)
        if not voice_id:
            raise ValueError(f"Missing ElevenLabs voice ID for speaker: {speaker_key}")

        output_format = elevenlabs_config.get("output_format", "mp3_44100_128")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format={output_format}"
        payload = {
            "text": text,
            "model_id": elevenlabs_config.get("model_id", "eleven_multilingual_v2"),
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "xi-api-key": api_key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        timeout_seconds = float(elevenlabs_config.get("timeout_seconds", 60))
        output_path = self._output_path(speaker_key, text)
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            output_path.write_bytes(response.read())
        return str(output_path)

    def _elevenlabs_config(self) -> dict:
        tts_config = self.config.get("tts", {}) if isinstance(self.config, dict) else {}
        elevenlabs_config = tts_config.get("elevenlabs", {}) if isinstance(tts_config, dict) else {}
        return elevenlabs_config if isinstance(elevenlabs_config, dict) else {}

    def _output_path(self, speaker_key: str, text: str) -> pathlib.Path:
        output_dir = pathlib.Path(self.config.get("output_dir", tempfile.gettempdir())) / "tts"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{speaker_key}_{self._safe_hash(text)}.mp3"

    def _safe_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
