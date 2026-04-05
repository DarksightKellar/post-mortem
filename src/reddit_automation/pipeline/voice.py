from reddit_automation.clients.tts_client import TTSClient
from reddit_automation.utils.ffmpeg import stitch_audio_clips


def _generate_temp_audio_path(config: dict, index: int) -> str:
    import tempfile
    import pathlib
    output_dir = pathlib.Path(tempfile.gettempdir()) / "reddit_automation_tts"
    output_dir.mkdir(exist_ok=True)
    return str(output_dir / f"line_{index}.mp3")


def generate_episode_audio(script: dict, config: dict) -> str:
    """Generate and stitch host audio tracks."""
    client = TTSClient(config)
    audio_paths = []

    for line in script.get("cold_open", {}).get("lines", []):
        audio_paths.append(client.generate(line["speaker"], line["text"]))

    for segment in script.get("segments", []):
        for line in segment.get("lines", []):
            audio_paths.append(client.generate(line["speaker"], line["text"]))

    for line in script.get("outro", {}).get("lines", []):
        audio_paths.append(client.generate(line["speaker"], line["text"]))

    output_path = str(config.get("output_dir", "/tmp")) + "/episode_audio.mp3"
    return stitch_audio_clips(audio_paths, output_path)
