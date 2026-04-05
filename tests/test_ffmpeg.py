"""Unit tests for ffmpeg render_video with generated scene assets."""

import subprocess
from reddit_automation.utils.ffmpeg import render_video


def test_render_video_builds_slideshow_cmd_when_scene_images_provided(monkeypatch, tmp_path):
    """When scene_images are provided, render_video should use a slideshow command."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"fake audio")
    output_path = tmp_path / "output.mp4"

    scene_images = [
        str(tmp_path / "scene_1.png"),
        str(tmp_path / "scene_2.png"),
        str(tmp_path / "scene_3.png"),
    ]

    config = {
        "render": {
            "resolution": "1920x1080",
            "fps": 30,
        }
    }

    captured_cmds = []

    def fake_run(cmd, **kwargs):
        captured_cmds.append(cmd)
        if "ffprobe" in cmd[0]:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="30.0", stderr="")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    render_video(
        audio_path=str(audio_path),
        visual_plan={"scenes": [{"type": "title_card"}, {"type": "segment"}, {"type": "outro"}]},
        output_path=str(output_path),
        config=config,
        scene_images=scene_images,
    )

    assert len(captured_cmds) == 2
    # ffprobe first
    assert "ffprobe" in captured_cmds[0][0]
    # ffmpeg second
    assert captured_cmds[1][0] == "ffmpeg"
    assert "-f" in captured_cmds[1]
    assert "concat" in captured_cmds[1]
    # Should reference all scene images via the generated list file
    list_file = [c for c in captured_cmds[1] if "img_list.txt" in c]
    assert len(list_file) > 0


def test_render_video_falls_back_to_solid_color_when_no_scene_images(monkeypatch, tmp_path):
    """When no scene_images provided, render_video should use the original solid-color approach."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"fake audio")
    output_path = tmp_path / "output.mp4"

    config = {
        "render": {
            "resolution": "1920x1080",
            "fps": 30,
        }
    }

    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    render_video(
        audio_path=str(audio_path),
        visual_plan={"scenes": []},
        output_path=str(output_path),
        config=config,
        scene_images=None,
    )

    assert len(captured_cmd) == 1
    cmd = captured_cmd[0]
    assert cmd[0] == "ffmpeg"
    has_lavfi_color = any("color" in a and "lavfi" in cmd for a in cmd)
    assert has_lavfi_color


def test_render_video_raises_on_ffprobe_failure(monkeypatch, tmp_path):
    """render_video should raise RuntimeError when ffprobe fails."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"fake audio")
    output_path = tmp_path / "output.mp4"
    scene_images = [str(tmp_path / "scene_1.png")]

    config = {
        "render": {"resolution": "1920x1080", "fps": 30},
    }

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr="ffprobe error"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        render_video(
            audio_path=str(audio_path),
            visual_plan={"scenes": [{"type": "title_card"}]},
            output_path=str(output_path),
            config=config,
            scene_images=scene_images,
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "ffprobe" in str(e).lower()


def test_render_video_raises_on_ffmpeg_failure(monkeypatch, tmp_path):
    """render_video should raise RuntimeError when ffmpeg fails after successful ffprobe."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"fake audio")
    output_path = tmp_path / "output.mp4"
    scene_images = [str(tmp_path / "scene_1.png")]

    config = {
        "render": {"resolution": "1920x1080", "fps": 30},
    }

    call_count = [0]

    def fake_run(cmd, **kwargs):
        call_count[0] += 1
        if "ffprobe" in cmd[0]:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="30.0", stderr="")
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr="ffmpeg error"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        render_video(
            audio_path=str(audio_path),
            visual_plan={"scenes": [{"type": "title_card"}]},
            output_path=str(output_path),
            config=config,
            scene_images=scene_images,
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "ffmpeg" in str(e).lower()
