class TTSClient:
    """Thin wrapper around edge-tts for free TTS without API keys."""
    def __init__(self, config: dict):
        self.config = config
        self._speaker_id_map = {
            # Default edge-tts voices
            "host_1": "en-US-GuyNeural",
            "host_2": "en-US-AnaNeural",
        }

    def generate(self, speaker_key: str, text: str) -> str:
        """Generate audio for one line and return the path."""
        import asyncio
        import hashlib
        import tempfile
        import pathlib

        voice = self._speaker_id_map.get(speaker_key, "en-US-GuyNeural")
        output_dir = pathlib.Path(tempfile.gettempdir()) / "reddit_automation_tts"
        output_dir.mkdir(exist_ok=True)
        safe_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
        output_path = str(output_dir / f"{speaker_key}_{safe_hash}.mp3")

        import edge_tts
        asyncio.run(edge_tts.Communicate(text, voice).save(output_path))
        return output_path
