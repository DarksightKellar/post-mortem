import os
import subprocess
from pathlib import Path


def stitch_audio_clips(audio_paths: list[str], output_path: str) -> str:
    """Concatenate multiple audio clips into a single file using ffmpeg."""
    if not audio_paths:
        raise ValueError("No audio paths provided for stitching")

    list_file = output_path + ".list.txt"
    with open(list_file, "w") as f:
        for path in audio_paths:
            f.write(f"file '{path}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")

    os.remove(list_file)
    return output_path


def render_video(*, audio_path: str, visual_plan: dict, output_path: str, config: dict, scene_images: list = None) -> str:
    """Render a video using FFmpeg with audio and visual scenes.

    When scene_images are provided, builds a slideshow with one image per scene.
    Falls back to a solid black background when no scene images are available.

    PERFORMANCE NOTE: The concat demuxer with duration tags is used to produce
    a timed slideshow. Each image gets equal screen time (audio_duration / num_images).
    For large videos (>100MB output), ffmpeg's stillimage tune and libx264 encoding
    can be slow. If render times become a bottleneck, consider:
    - Lowering fps from 30 to 24
    - Using -preset faster or -preset ultrafast
    - Pre-generating a base video with ffmpeg instead of concatenating images at runtime
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    resolution = config.get("render", {}).get("resolution", "1920x1080")
    fps = config.get("render", {}).get("fps", 30)

    if scene_images:
        num_scenes = len(scene_images)

        # Get audio duration from ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if probe_result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {probe_result.stderr}")

        audio_duration = float(probe_result.stdout.strip())
        duration_per_scene = audio_duration / num_scenes

        # Build concat demuxer file with durations
        list_file = output_path + ".img_list.txt"
        with open(list_file, "w") as f:
            for img in scene_images:
                f.write(f"file '{img}'\n")
                f.write(f"duration {duration_per_scene}\n")
            f.write(f"file '{scene_images[-1]}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg render failed: {result.stderr}")

        os.remove(list_file)
    else:
        # Fallback: solid black background
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={resolution}:r={fps}",
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg render failed: {result.stderr}")

    return output_path
